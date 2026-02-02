"""
Обработчики команд и сообщений бота.
"""
from telegram_bot.handlers import menu
from telegram_bot.handlers import master
from telegram_bot.handlers import polishing
from telegram_bot.handlers import otk
from telegram_bot.handlers import urgent
from telegram_bot.handlers import history
from telegram_bot.handlers import employees

__all__ = ["menu", "master", "polishing", "otk", "urgent", "history", "employees"]
