"""
Обработчики команд и сообщений бота.
"""
from telegram_bot.handlers import menu
from telegram_bot.handlers import new_receipt
from telegram_bot.handlers import operations
from telegram_bot.handlers import polishing
from telegram_bot.handlers import otk
from telegram_bot.handlers import history

__all__ = ["menu", "new_receipt", "operations", "polishing", "otk", "history"]
