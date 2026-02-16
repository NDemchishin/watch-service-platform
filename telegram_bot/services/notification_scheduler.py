"""
Фоновая задача для отправки уведомлений о дедлайнах.
Проверяет pending уведомления каждые 60 секунд и отправляет их OTK-пользователям.
"""
import asyncio
import logging
from datetime import datetime

from aiogram import Bot

from telegram_bot.config import bot_config
from telegram_bot.services.api_client import get_api_client
from telegram_bot.utils import format_datetime

logger = logging.getLogger(__name__)

# Интервал проверки в секундах
CHECK_INTERVAL = 60

# Тексты уведомлений
NOTIFICATION_MESSAGES = {
    "deadline_today": "📅 Сегодня дедлайн по квитанции №{receipt_number}",
    "deadline_1h": "⏰ Через 1 час дедлайн по квитанции №{receipt_number}",
    "deadline_changed": (
        "📅 Дедлайн по квитанции №{receipt_number} изменён:\n"
        "{old_deadline} → {new_deadline}\n"
        "Изменил: @{username}"
    ),
}


async def send_notification_to_otk(bot: Bot, text: str) -> int:
    """
    Отправляет уведомление всем OTK-пользователям (из ADMIN_IDS).
    Возвращает количество успешно отправленных сообщений.
    """
    sent = 0
    recipients = bot_config.ADMIN_IDS
    if not recipients:
        logger.warning("No ADMIN_IDS configured, cannot send notifications")
        return 0

    for user_id in recipients:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")

    return sent


async def process_pending_notifications(bot: Bot) -> None:
    """Обрабатывает одну итерацию проверки уведомлений."""
    try:
        api = get_api_client()
        pending = await api.get_pending_notifications()

        for notif in pending:
            notification_id = notif.get("id")
            receipt_id = notif.get("receipt_id")
            notif_type = notif.get("notification_type")

            # Получаем квитанцию для номера
            try:
                receipt = await api.get_receipt(receipt_id)
                receipt_number = receipt.get("receipt_number", str(receipt_id))
            except Exception:
                receipt_number = str(receipt_id)

            # Формируем текст
            template = NOTIFICATION_MESSAGES.get(notif_type, "🔔 Уведомление по квитанции №{receipt_number}")
            text = template.format(receipt_number=receipt_number)

            # Отправляем
            sent = await send_notification_to_otk(bot, text)

            # Помечаем как отправленное
            if sent > 0:
                try:
                    await api.mark_notification_sent(notification_id)
                    logger.info(f"Notification {notification_id} sent to {sent} users")
                except Exception as e:
                    logger.error(f"Failed to mark notification {notification_id} as sent: {e}")

    except Exception as e:
        logger.error(f"Error processing notifications: {e}")


async def run_notification_scheduler(bot: Bot) -> None:
    """Запускает бесконечный цикл проверки уведомлений."""
    logger.info("Notification scheduler started")
    while True:
        await process_pending_notifications(bot)
        await asyncio.sleep(CHECK_INTERVAL)
