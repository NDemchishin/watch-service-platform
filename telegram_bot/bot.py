"""
Главный файл Telegram бота на aiogram 3.x.
Согласно ТЗ п. 12: используем aiogram 3.x.
"""
import logging
import asyncio
from datetime import timedelta
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import TelegramObject

from telegram_bot.config import bot_config
from telegram_bot.states import MainMenu
from telegram_bot.services.notification_scheduler import run_notification_scheduler

# Импорт роутеров (прямой импорт для избежания проблем сcircular imports)
from telegram_bot.handlers import menu
from telegram_bot.handlers import master
from telegram_bot.handlers import polishing
from telegram_bot.handlers import otk
from telegram_bot.handlers import urgent
from telegram_bot.handlers import history
from telegram_bot.handlers import employees
from telegram_bot.handlers import analytics

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Глобальный middleware для обработки ошибок в хендлерах."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception("Handler error: %s", e)
            state = data.get("state")
            if state:
                await state.clear()


def create_dispatcher() -> Dispatcher:
    """Создает и настраивает диспетчер."""
    storage = RedisStorage.from_url(
        bot_config.REDIS_URL,
        state_ttl=timedelta(hours=24),
        data_ttl=timedelta(hours=24),
    )
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутеры в правильном порядке (от общего к частному)
    dp.include_router(menu.router)
    dp.include_router(master.router)
    dp.include_router(polishing.router)
    dp.include_router(otk.router)
    dp.include_router(urgent.router)
    dp.include_router(history.router)
    dp.include_router(employees.router)
    dp.include_router(analytics.router)

    # Глобальный middleware для обработки ошибок
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())

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

    # Запускаем фоновый scheduler уведомлений
    asyncio.create_task(run_notification_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


# Глобальные объекты для webhook
_bot: Bot = None
_dp: Dispatcher = None
_scheduler_started: bool = False


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
    global _scheduler_started

    if not bot_config.WEBHOOK_URL:
        logger.warning("WEBHOOK_URL not set, skipping webhook setup")
        return

    bot = get_bot()
    base_url = bot_config.WEBHOOK_URL.rstrip('/')
    # Remove /webhook suffix if present to avoid duplication
    if base_url.endswith('/webhook'):
        base_url = base_url[:-8]
    # Route is: /webhook/telegram/webhook
    webhook_url = f"{base_url}/webhook/telegram/webhook"

    # Pass secret_token so Telegram sends X-Telegram-Bot-Api-Secret-Token header
    webhook_kwargs = {"url": webhook_url}
    if bot_config.WEBHOOK_SECRET:
        webhook_kwargs["secret_token"] = bot_config.WEBHOOK_SECRET
    await bot.set_webhook(**webhook_kwargs)
    logger.info(f"Webhook set to: {webhook_url}")

    # Запускаем фоновый scheduler уведомлений (только один раз)
    if not _scheduler_started:
        _scheduler_started = True
        asyncio.create_task(run_notification_scheduler(bot))
        logger.info("Notification scheduler started as background task")
    else:
        logger.info("Notification scheduler already running, skipping")


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
