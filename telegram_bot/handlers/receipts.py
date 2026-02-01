"""
Обработчики для работы с квитанциями.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
api_client = APIClient()


async def list_receipts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /receipts - показывает список квитанций."""
    logger.info("Listing receipts")
    
    try:
        # Получаем список квитанций из API
        receipts = await api_client.get_receipts(skip=0, limit=10)
        
        if not receipts:
            await update.message.reply_text("📋 Квитанции не найдены.")
            return
        
        # Формируем сообщение со списком квитанций
        message = "📋 Последние квитанции:\n\n"
        for receipt in receipts:
            status = "✅" if receipt.get("is_completed") else "⏳"
            message += (
                f"{status} №{receipt.get('receipt_number', 'N/A')} - "
                f"{receipt.get('client_name', 'Unknown')}\n"
                f"   Часы: {receipt.get('watch_brand', 'N/A')} {receipt.get('watch_model', '')}\n\n"
            )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error fetching receipts: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении списка квитанций.\n"
            "Пожалуйста, попробуйте позже."
        )


async def get_receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для получения деталей квитанции."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Пожалуйста, укажите номер квитанции.\n"
            "Пример: /receipt 123"
        )
        return
    
    try:
        receipt_id = int(args[0])
        logger.info(f"Fetching receipt {receipt_id}")
        
        receipt = await api_client.get_receipt(receipt_id)
        
        # Формируем детальное сообщение о квитанции
        status = "✅ Завершена" if receipt.get("is_completed") else "⏳ В работе"
        message = (
            f"📋 Квитанция №{receipt.get('receipt_number')}\n"
            f"Статус: {status}\n\n"
            f"👤 Клиент: {receipt.get('client_name', 'N/A')}\n"
            f"📞 Телефон: {receipt.get('client_phone', 'N/A')}\n\n"
            f"⌚ Часы:\n"
            f"   Бренд: {receipt.get('watch_brand', 'N/A')}\n"
            f"   Модель: {receipt.get('watch_model', 'N/A')}\n"
            f"   Серийный номер: {receipt.get('serial_number', 'N/A')}\n\n"
            f"🔧 Неисправность:\n"
            f"{receipt.get('issue_description', 'Нет описания')}\n\n"
        )
        
        if receipt.get("estimated_cost"):
            message += f"💰 Предварительная стоимость: {receipt.get('estimated_cost')} руб.\n"
        
        if receipt.get("prepaid_amount"):
            message += f"💵 Предоплата: {receipt.get('prepaid_amount')} руб.\n"
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат номера квитанции.\n"
            "Используйте только цифры."
        )
    except Exception as e:
        logger.error(f"Error fetching receipt: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении квитанции.\n"
            "Проверьте номер и попробуйте снова."
        )


# Для совместимости с импортом в __init__.py
receipts_handler = {
    "receipts": list_receipts_command,
    "receipt": get_receipt_command,
}
