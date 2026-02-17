"""
Утилитарные функции для Telegram-бота.
"""
import logging
from datetime import datetime
from typing import Optional

from aiogram.fsm.context import FSMContext

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


async def push_nav(state: FSMContext, current_state: str, handler_name: str) -> None:
    """Сохранить текущее состояние в стек навигации."""
    data = await state.get_data()
    history = data.get("nav_history", [])
    history.append({"state": current_state, "handler": handler_name})
    await state.update_data(nav_history=history)


async def pop_nav(state: FSMContext) -> Optional[dict]:
    """Извлечь предыдущее состояние из стека навигации."""
    data = await state.get_data()
    history = data.get("nav_history", [])
    if history:
        prev = history.pop()
        await state.update_data(nav_history=history)
        return prev
    return None
