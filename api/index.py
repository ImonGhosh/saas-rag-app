from unittest import result
from fastapi import FastAPI  # type: ignore
from fastapi import UploadFile, File  # type: ignore
from fastapi.responses import PlainTextResponse  # type: ignore
from pydantic import BaseModel  # type: ignore
from openai import OpenAI  # type: ignore
from supabase import create_client, Client
from openai import AsyncOpenAI

from dotenv import load_dotenv
from pathlib import Path
import os
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


# @app.post("/api", response_class=PlainTextResponse)
# async def idea(payload: IdeaRequest):
#     try:
#         db_response = (
#             supabase
#             .from_("website_pages")
#             .select("metadata->>source, metadata->>topic")
#             .execute()
#         )

#         if db_response.data:
#             source_value = db_response.data[0]['source']
#             print("Source:", source_value)
#             topic_value = db_response.data[0]['topic']
#             print("Topic:", topic_value)

#             rag_agent_web.doc_name = source_value
#             rag_agent_web.topic_name = topic_value
#             print(f'Document Name: {rag_agent_web.doc_name}')
#             print(f'Topic Name: {rag_agent_web.topic_name}')
#         else:
#             print("No data found.")

#     except Exception as e:
#         print(f"Error: {db_response.status_code} - {db_response.message}")

#     response = await rag_agent_web.pydantic_ai_expert.run(payload.text, deps=DEPS)
#     if hasattr(response, "data"):
#         return str(response.data)
#     for attr in ("output", "output_text", "text"):
#         if hasattr(response, attr):
#             return str(getattr(response, attr))
#     return str(response)


@app.post("/api", response_class=PlainTextResponse)
async def idea(payload: IdeaRequest):

    response = await rag_agent_file.agent.run(payload.text)
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


@app.post("/ingest-file", response_class=PlainTextResponse)
async def ingest_file(file: UploadFile = File(...)):
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

    try:
        # Run the ingestion pipeline over files in api/documents. This awaits completion.
        await file_data_ingest.run_ingestion()
    except Exception as err:
        return f"Error: {err}"

    return "Successfully ingested the document"
    
