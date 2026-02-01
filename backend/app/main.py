"""
Главный файл FastAPI приложения.
"""
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title=settings.APP_TITLE)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
