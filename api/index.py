from fastapi import FastAPI  # type: ignore
from fastapi.responses import PlainTextResponse  # type: ignore
from openai import OpenAI  # type: ignore

from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

# Prefer OPENAI_API_KEY, but fall back to OPEN_AI_API_KEY if that's what you used
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

app = FastAPI()


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


@app.get("/api", response_class=PlainTextResponse)
def idea():
    prompt = [{"role": "user", "content": "Come up with a productivity plan for me for tomorrow."}]
    response = client.chat.completions.create(model="gpt-5-nano", messages=prompt)
    return response.choices[0].message.content