"""
Главный файл Telegram бота на aiogram 3.x.
Согласно ТЗ п. 12: используем aiogram 3.x.
"""
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from telegram_bot.config import bot_config
from telegram_bot.states import MainMenu

# Импорт роутеров
from telegram_bot.handlers import menu, new_receipt, operations, polishing, otk, history

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    """Создает и настраивает диспетчер бота."""
    # Создаем диспетчер
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(menu.router)
    dp.include_router(new_receipt.router)
    dp.include_router(operations.router)
    dp.include_router(polishing.router)
    dp.include_router(otk.router)
    dp.include_router(history.router)
    
    logger.info("Dispatcher created with all routers")
    return dp


async def start_polling():
    """Запускает бота в режиме polling (для локальной разработки)."""
    # Проверяем конфигурацию
    bot_config.validate()
    
    # Создаем бота с DefaultBotProperties
    bot = Bot(
        token=bot_config.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = create_dispatcher()
    
    logger.info("Starting bot in polling mode...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


# Глобальные объекты для webhook
_bot: Bot = None
_dp: Dispatcher = None


def get_bot() -> Bot:
    """Возвращает глобальный объект бота."""
    global _bot
    if _bot is None:
        bot_config.validate()
        _bot = Bot(
            token=bot_config.TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return _bot


def get_dispatcher() -> Dispatcher:
    """Возвращает глобальный диспетчер."""
    global _dp
    if _dp is None:
        _dp = create_dispatcher()
    return _dp


async def setup_webhook() -> None:
    """Настраивает webhook для бота."""
    if not bot_config.WEBHOOK_URL:
        logger.warning("WEBHOOK_URL not set, skipping webhook setup")
        return
    
    bot = get_bot()
    webhook_url = f"{bot_config.WEBHOOK_URL}/webhook"
    
    await bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")


async def process_update(update_data: dict) -> None:
    """Обрабатывает обновление от Telegram (для webhook)."""
    from aiogram.types import Update
    
    bot = get_bot()
    dp = get_dispatcher()
    
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    # Для локального запуска в режиме polling
    asyncio.run(start_polling())
