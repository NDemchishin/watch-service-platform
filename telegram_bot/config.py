"""
Конфигурация Telegram бота.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """Конфигурация бота."""

    # Telegram Bot Token - никогда не коммитить в репозиторий!
    TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Webhook URL для продакшена
    WEBHOOK_URL: str = os.getenv("TELEGRAM_BOT_WEBHOOK_URL", "")

    # ID администраторов бота
    ADMIN_IDS: list[int] = [
        int(id_str.strip())
        for id_str in os.getenv("BOT_ADMIN_IDS", "").split(",")
        if id_str.strip()
    ]

    # URL API бэкенда
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

    @classmethod
    def validate(cls) -> bool:
        """Проверяет, что все необходимые переменные окружения установлены."""
        if not cls.TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN не установлен! "
                "Пожалуйста, создайте .env файл на основе .env.example"
            )
        return True


bot_config = BotConfig()
