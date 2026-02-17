"""
Главный файл FastAPI приложения.
"""
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.api import api_router
from app.api.telegram import router as telegram_router

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    description="API для системы учета производства и качества в часовой мастерской",
    version="1.0.0",
)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )


# CORS middleware — разрешённые домены из переменной окружения
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check endpoint with database verification."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)},
        )

# Подключаем webhook endpoint напрямую (без префикса /api/v1)
app.include_router(telegram_router, prefix="/webhook")

# Подключаем API роутер
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Действия при старте приложения."""
    logger.info("Application startup")


@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения."""
    logger.info("Application shutdown")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
