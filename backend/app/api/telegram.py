"""
API endpoints для Telegram бота webhook.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from telegram_bot.bot import setup_webhook, process_update, get_bot_application
from telegram_bot.config import bot_config

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
        
        # Получаем приложение бота
        application = get_bot_application()
        
        # Инициализируем приложение
        await application.initialize()
        logger.info("Bot application initialized")
        
        # Настраиваем webhook если есть URL
        if bot_config.WEBHOOK_URL:
            await setup_webhook()
            logger.info(f"Webhook configured for URL: {bot_config.WEBHOOK_URL}")
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
            application = get_bot_application()
            await application.shutdown()
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
    
    if not _bot_initialized:
        logger.error("Bot not initialized, cannot process webhook")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot not initialized"
        )
    
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


@router.get("/health")
async def bot_health() -> dict:
    """Health check endpoint для бота."""
    global _bot_initialized
    
    return {
        "bot_initialized": _bot_initialized,
        "token_configured": bool(bot_config.TOKEN),
        "webhook_url": bot_config.WEBHOOK_URL if bot_config.WEBHOOK_URL else None,
    }


@router.get("/info")
async def bot_info() -> dict:
    """Информация о боте (только для администраторов)."""
    try:
        application = get_bot_application()
        bot = application.bot
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        return {
            "bot_id": bot_info.id,
            "bot_username": bot_info.username,
            "bot_name": bot_info.first_name,
            "can_join_groups": bot_info.can_join_groups,
            "can_read_all_group_messages": bot_info.can_read_all_group_messages,
            "supports_inline_queries": bot_info.supports_inline_queries,
        }
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bot info: {str(e)}"
        )
