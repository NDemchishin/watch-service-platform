"""
Утилитарные функции для Telegram-бота.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def format_datetime(iso_string: str, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """
    Парсит ISO-строку даты и возвращает отформатированную строку.
    При невалидной дате логирует warning и возвращает исходную строку как fallback.
    """
    if not iso_string:
        return "не указан"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse datetime '{iso_string}': {e}")
        return iso_string
