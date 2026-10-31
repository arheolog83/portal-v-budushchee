from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


app = FastAPI(
    title="Портал в будущее",
    description="Инструменты для учителей 5–11 классов",
    version="0.1.0",
)

INDEX_FILE = Path(__file__).with_name("index.html")


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(INDEX_FILE)
