"""
Конфигурация приложения.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    """Получает обязательную переменную окружения."""
    value = os.getenv(name, "")
    if not value:
        raise ValueError(f"Обязательная переменная окружения {name} не установлена")
    return value


class Settings:
    """Настройки приложения."""

    # Database — без дефолта, приложение не запустится без БД
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # FastAPI
    APP_TITLE: str = "Watch Service Platform"
    DEBUG: bool = False

    # API Security — без дефолтов
    API_KEY: str = os.getenv("API_KEY", "")
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # CORS — по умолчанию пустой (ничего не разрешено)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_WEBHOOK_URL: str = os.getenv("TELEGRAM_BOT_WEBHOOK_URL", "")
    BOT_ADMIN_IDS: list[int] = [
        int(id_str.strip())
        for id_str in os.getenv("BOT_ADMIN_IDS", "").split(",")
        if id_str.strip()
    ]

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


settings = Settings()
