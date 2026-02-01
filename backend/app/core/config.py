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

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_WEBHOOK_URL: str = os.getenv("TELEGRAM_BOT_WEBHOOK_URL", "")
    BOT_ADMIN_IDS: list[int] = [
        int(id_str.strip())
        for id_str in os.getenv("BOT_ADMIN_IDS", "").split(",")
        if id_str.strip()
    ]


settings = Settings()
