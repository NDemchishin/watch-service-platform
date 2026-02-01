"""
Конфигурация приложения.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Настройки приложения."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:password@localhost:5432/watch_service"
    )

    # FastAPI
    APP_TITLE: str = "Watch Service Platform"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings()
