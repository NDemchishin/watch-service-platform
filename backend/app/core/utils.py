"""
Утилиты приложения.
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def now_moscow() -> datetime:
    """Текущее время в московском часовом поясе."""
    return datetime.now(MOSCOW_TZ)


def format_datetime(dt: datetime) -> str:
    """Форматирует datetime в московское время (ДД.ММ.ГГГГ ЧЧ:ММ)."""
    if dt is None:
        return "—"
    return dt.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")


def sanitize_text(text: str | None, max_length: int = 1000) -> str | None:
    """Очистить текст от управляющих символов и ограничить длину."""
    if text is None:
        return None
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:max_length].strip()
