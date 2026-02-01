"""
Главный файл Telegram бота.
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from telegram_bot.config import bot_config

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
MAIN_MENU, SEARCH_RECEIPT, RECEIPT_DETAILS = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для учета производства и качества в часовой мастерской.\n\n"
        "📋 Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать справку\n"
        "/search - Поиск квитанции по номеру\n"
        "/receipts - Список последних квитанций\n"
    )
    
    await update.message.reply_text(welcome_text)
    return MAIN_MENU


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


async def search_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /search."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Пожалуйста, укажите номер квитанции.\n"
            "Пример: /search 123"
        )
        return
    
    receipt_number = args[0]
    logger.info(f"Searching for receipt: {receipt_number}")
    
    # TODO: Интеграция с API для поиска квитанции
    await update.message.reply_text(
        f"🔍 Ищу квитанцию №{receipt_number}...\n"
        "(Функция в разработке)"
    )


async def list_receipts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /receipts."""
    logger.info("Listing receipts")
    
    # TODO: Интеграция с API для получения списка квитанций
    await update.message.reply_text(
        "📋 Список квитанций:\n"
        "(Функция в разработке)"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений."""
    text = update.message.text
    logger.info(f"Received message: {text}")
    
    # Если сообщение похоже на номер квитанции (только цифры)
    if text.isdigit():
        await update.message.reply_text(
            f"🔍 Ищу квитанцию №{text}...\n"
            "Используйте /search <номер> для поиска"
        )
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду.\n"
            "Используйте /help для просмотра доступных команд."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        )


def create_application() -> Application:
    """Создает и настраивает приложение бота."""
    # Проверяем конфигурацию
    bot_config.validate()
    
    # Создаем приложение
    application = Application.builder().token(bot_config.TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_receipt))
    application.add_handler(CommandHandler("receipts", list_receipts))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Bot application created successfully")
    return application


# Глобальное приложение для использования в webhook
_bot_application = None


def get_bot_application() -> Application:
    """Возвращает глобальное приложение бота (singleton)."""
    global _bot_application
    if _bot_application is None:
        _bot_application = create_application()
    return _bot_application


async def setup_webhook() -> None:
    """Настраивает webhook для бота."""
    if not bot_config.WEBHOOK_URL:
        logger.warning("WEBHOOK_URL not set, skipping webhook setup")
        return
    
    application = get_bot_application()
    webhook_url = f"{bot_config.WEBHOOK_URL}/webhook"
    
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")


async def process_update(update_data: dict) -> None:
    """Обрабатывает обновление от Telegram (для webhook)."""
    application = get_bot_application()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)


if __name__ == "__main__":
    # Для локального запуска в режиме polling
    import asyncio
    
    async def main():
        application = create_application()
        logger.info("Starting bot in polling mode...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Держим бота запущенным
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
    
    asyncio.run(main())
