"""
Клавиатуры для Telegram бота.
"""
from telegram_bot.keyboards.main_menu import (
    get_main_menu_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_confirm_keyboard,
)

__all__ = [
    "get_main_menu_keyboard",
    "get_back_keyboard",
    "get_cancel_keyboard",
    "get_confirm_keyboard",
]
