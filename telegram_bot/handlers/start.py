"""
Обработчик команды /start и базовых команд.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для учета производства и качества в часовой мастерской.\n\n"
        "📋 Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/search <номер> - Поиск квитанции по номеру\n"
        "/receipts - Список последних квитанций\n"
    )
    
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📖 Справка по использованию бота:\n\n"
        "Этот бот помогает отслеживать квитанции и операции в часовой мастерской.\n\n"
        "📋 Команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/search <номер> - Найти квитанцию по номеру\n"
        "/receipts - Показать список последних квитанций\n\n"
        "🔍 Для поиска квитанции введите номер или используйте команду /search"
    )
    await update.message.reply_text(help_text)


# Для совместимости с импортом в __init__.py
start_handler = {
    "start": start_command,
    "help": help_command,
}
