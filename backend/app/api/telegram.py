"""
API endpoints для Telegram бота webhook.
Обновлен для работы с aiogram 3.x
"""
import logging
import asyncio
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from telegram_bot.bot import setup_webhook, process_update, get_bot, get_dispatcher
from telegram_bot.config import bot_config
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

# Флаг для отслеживания инициализации бота
_bot_initialized = False


@router.on_event("startup")
async def startup_event():
    """Инициализация бота при старте приложения."""
    global _bot_initialized
    
    try:
        logger.info("Initializing Telegram bot...")
        
        # Проверяем конфигурацию
        if not bot_config.TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set, bot will not be initialized")
            return
        
        # Получаем бота и диспетчер
        bot = get_bot()
        dp = get_dispatcher()
        
        # Настраиваем webhook если есть URL
        if bot_config.WEBHOOK_URL:
            # Добавляем задержку перед установкой webhook
            await asyncio.sleep(2)
            try:
                await setup_webhook()
                logger.info(f"Webhook configured for URL: {bot_config.WEBHOOK_URL}")
            except Exception as e:
                logger.warning(f"Could not set webhook immediately: {e}")
                # Попробуем еще раз через 5 секунд
                await asyncio.sleep(5)
                try:
                    await setup_webhook()
                    logger.info(f"Webhook configured on retry for URL: {bot_config.WEBHOOK_URL}")
                except Exception as e2:
                    logger.error(f"Failed to set webhook on retry: {e2}")
        else:
            logger.warning("WEBHOOK_URL not set, webhook not configured")
        
        _bot_initialized = True
        logger.info("Telegram bot startup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        # Не прерываем запуск приложения из-за ошибки бота


@router.on_event("shutdown")
async def shutdown_event():
    """Завершение работы бота при остановке приложения."""
    global _bot_initialized
    
    if _bot_initialized:
        try:
            logger.info("Shutting down Telegram bot...")
            bot = get_bot()
            await bot.session.close()
            logger.info("Bot shutdown completed")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")


@router.post("/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    """
    Endpoint для получения webhook от Telegram.
    
    Telegram отправляет обновления (сообщения, команды) на этот endpoint.
    """
    global _bot_initialized
    
    # Verify webhook secret
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    try:
        # Получаем данные от Telegram
        update_data = await request.json()
        logger.debug(f"Received webhook data: {update_data}")
        
        # Обрабатываем обновление
        await process_update(update_data)
        
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Возвращаем 200 OK даже при ошибке, чтобы Telegram не повторял запрос
        # Логируем ошибку для отладки
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=status.HTTP_200_OK
        )
