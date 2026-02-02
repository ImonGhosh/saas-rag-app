from unittest import result
from fastapi import FastAPI  # type: ignore
from fastapi import BackgroundTasks, HTTPException  # type: ignore
from fastapi import UploadFile, File  # type: ignore
from fastapi.responses import PlainTextResponse  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from pydantic import BaseModel  # type: ignore
from openai import OpenAI  # type: ignore
from supabase import create_client, Client
from openai import AsyncOpenAI

from dotenv import load_dotenv
from pathlib import Path
import os
import asyncio
from uuid import uuid4
from fastapi.middleware.cors import CORSMiddleware

from . import rag_agent_web
from . import rag_agent_file
from . import web_data_ingestion
from .file_data_ingestion import ingest as file_data_ingest

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

# api_key = os.getenv("OPENAI_API_KEY")
# client = OpenAI(api_key=api_key)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Prepare dependencies
DEPS = rag_agent_web.PydanticAIDeps(
    supabase=supabase,
    openai_client=openai_client
)

app = FastAPI()

_INGEST_JOBS: dict[str, dict[str, str]] = {}
_INGEST_LOCK = asyncio.Lock()


async def _run_ingest_file_job(job_id: str) -> None:
    job = _INGEST_JOBS.get(job_id)
    if job is None:
        return

    job["status"] = "running"

    try:
        async with _INGEST_LOCK:
            await file_data_ingest.run_ingestion()
        job["status"] = "succeeded"
    except Exception as err:
        job["status"] = "failed"
        job["error"] = str(err)


class IdeaRequest(BaseModel):
    text: str


class IngestRequest(BaseModel):
    url: str

# Prevents accidental overwrites by saving as name (1).ext, name (2).ext, etc. if the filename already exists.
def _unique_path(path: Path) -> Path:
    """Return a non-existing path by suffixing ' (n)' if needed."""
    if not path.exists():
        return path

    
    # Splits filename into: stem: name without extension (report) and suffix: extension (.pdf)
    # Tries: report (1).pdf, report (2).pdf… until it finds a name that doesn’t exist.
    stem, suffix = path.stem, path.suffix
    i = 1
    while True:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1

# Configure CORS (allowed urls that can access this API)
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # optional but commonly needed
    allow_methods=["*"],      # Allow all HTTP methods(GET, POST etc.)
    allow_headers=["*"],      # IMPORTANT for JSON requests (Content-Type)
)

@app.post("/api", response_class=PlainTextResponse)
async def idea(payload: IdeaRequest):

    response = await rag_agent_file.agent.run(payload.text, deps=DEPS)
    if hasattr(response, "data"):
        return str(response.data)
    for attr in ("output", "output_text", "text"):
        if hasattr(response, attr):
            return str(getattr(response, attr))
    return str(response)


@app.post("/ingest", response_class=PlainTextResponse)
async def ingest(payload: IngestRequest):
    try:
        await web_data_ingestion.crawl_data(payload.url)

        # After crawl saves markdown into api/documents, run the file ingestion pipeline over those files.
        await file_data_ingest.run_ingestion()

        return "Sucessfully ingested website data"
    except Exception as err:
        return f"Error: {err}"


@app.post("/ingest-file", response_class=JSONResponse)
async def ingest_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Receives an uploaded file and stores it under the repo-relative `api/documents/` folder.
    """
    documents_dir = ROOT_DIR / "api" / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)

    # Avoid path traversal (e.g. "..\\..\\foo") by keeping only the base name.
    filename = Path(file.filename or "uploaded_file").name
    dest_path = _unique_path(documents_dir / filename)

    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                out.write(chunk)
    finally:
        await file.close()

    job_id = uuid4().hex
    _INGEST_JOBS[job_id] = {"status": "queued"}
    background_tasks.add_task(_run_ingest_file_job, job_id)

    return JSONResponse(status_code=202, content={"job_id": job_id})


@app.get("/ingest-file/status/{job_id}")
async def ingest_file_status(job_id: str):
    job = _INGEST_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JSONResponse(content=job)
    
