"""
Обработчики для поиска квитанций.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
api_client = APIClient()


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /search - поиск квитанции по номеру."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Пожалуйста, укажите номер квитанции.\n"
            "Пример: /search 123"
        )
        return
    
    search_query = args[0]
    logger.info(f"Searching for receipt: {search_query}")
    
    try:
        # Пробуем найти квитанцию по номеру
        receipt_id = int(search_query)
        receipt = await api_client.get_receipt(receipt_id)
        
        # Формируем сообщение с результатом
        status = "✅ Завершена" if receipt.get("is_completed") else "⏳ В работе"
        message = (
            f"📋 Квитанция №{receipt.get('receipt_number')}\n"
            f"Статус: {status}\n\n"
            f"👤 Клиент: {receipt.get('client_name', 'N/A')}\n"
            f"📞 Телефон: {receipt.get('client_phone', 'N/A')}\n\n"
            f"⌚ Часы: {receipt.get('watch_brand', 'N/A')} {receipt.get('watch_model', '')}\n"
            f"🔧 Неисправность: {receipt.get('issue_description', 'Нет описания')[:100]}...\n"
        )
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат номера квитанции.\n"
            "Используйте только цифры."
        )
    except Exception as e:
        logger.error(f"Error searching receipt: {e}")
        await update.message.reply_text(
            f"❌ Квитанция №{search_query} не найдена.\n"
            "Проверьте номер и попробуйте снова."
        )


async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений для поиска (если пользователь просто ввел номер)."""
    text = update.message.text.strip()
    
    # Если сообщение похоже на номер квитанции (только цифры)
    if text.isdigit():
        logger.info(f"Text search for receipt: {text}")
        
        # Создаем фиктивные args для использования search_command
        context.args = [text]
        await search_command(update, context)
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду.\n"
            "Используйте /help для просмотра доступных команд."
        )


# Для совместимости с импортом в __init__.py
search_handler = {
    "search": search_command,
    "text_search": handle_text_search,
}
