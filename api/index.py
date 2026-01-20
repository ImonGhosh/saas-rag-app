from fastapi import FastAPI  # type: ignore
from fastapi.responses import PlainTextResponse  # type: ignore
from openai import OpenAI  # type: ignore

from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

# Prefer OPENAI_API_KEY, but fall back to OPEN_AI_API_KEY if that's what you used
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

app = FastAPI()

@app.get("/api", response_class=PlainTextResponse)
def idea():
    prompt = [{"role": "user", "content": "Come up with a new business idea for AI Agents"}]
    response = client.chat.completions.create(model="gpt-5-nano", messages=prompt)
    return response.choices[0].message.content