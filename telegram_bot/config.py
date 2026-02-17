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

    # API ключ для авторизации запросов к бэкенду
    API_KEY: str = os.getenv("API_KEY", "")

    # Webhook secret для верификации запросов от Telegram
    WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # Redis URL для FSM storage
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # URL API бэкенда
    # Если не установлен, используем localhost (для Railway где бот и бэкенд в одном контейнере)
    API_BASE_URL: str = os.getenv("API_BASE_URL", "")
    
    @classmethod
    def get_api_base_url(cls) -> str:
        """Получает URL API бэкенда."""
        if cls.API_BASE_URL:
            return cls.API_BASE_URL
        # По умолчанию localhost (для Railway где бот и бэкенд в одном контейнере)
        # Бэкенд запущен на порту 8080
        return "http://localhost:8080"

    # Порт для webhook
    PORT: int = int(os.getenv("PORT", 8000))

    # Whitelist Telegram ID - только эти пользователи могут использовать бота
    ALLOWED_TELEGRAM_IDS: list[int] = [
        int(id_str.strip())
        for id_str in os.getenv("TELEGRAM_ALLOWED_IDS", "").split(",")
        if id_str.strip()
    ]

    @classmethod
    def validate(cls) -> bool:
        """Проверяет, что все необходимые переменные окружения установлены."""
        if not cls.TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN не установлен! "
                "Пожалуйста, создайте .env файл на основе .env.example"
            )
        return True

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return user_id in cls.ADMIN_IDS

    @classmethod
    def is_allowed(cls, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя доступ к боту (whitelist)."""
        # Если whitelist пустой, разрешаем всем (для разработки)
        if not cls.ALLOWED_TELEGRAM_IDS:
            return True
        return user_id in cls.ALLOWED_TELEGRAM_IDS


bot_config = BotConfig()
