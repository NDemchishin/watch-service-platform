"""
Безопасность и аутентификация.
"""
import logging

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.API_KEY:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
