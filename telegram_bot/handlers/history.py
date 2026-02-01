"""
Обработчики для просмотра истории.
Согласно ТЗ п. 11: история действий.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import History
from telegram_bot.keyboards.main_menu import get_back_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:history")
async def start_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало просмотра истории."""
    await callback.message.edit_text(
        text="📜 История\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(History.waiting_for_receipt_number)
    await callback.answer()


@router.message(History.waiting_for_receipt_number)
async def process_receipt_number(message: Message, state: FSMContext) -> None:
    """Обработка ввода номера квитанции."""
    receipt_number = message.text.strip()
    
    if not receipt_number.isdigit():
        await message.answer(
            text="❌ Номер квитанции должен содержать только цифры.\n\n"
                 "Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
        return
    
    try:
        # Ищем квитанцию по номеру
        receipt = await api_client.get_receipt_by_number(receipt_number)
        receipt_id = receipt.get("id")
        
        # Получаем историю
        history = await api_client.get_receipt_history(receipt_id)
        
        if not history:
            message_text = f"📜 История квитанции №{receipt_number}\n\nИстория пуста."
        else:
            message_text = f"📜 История квитанции №{receipt_number}\n\n"
            for event in history:
                event_type = event.get("event_type", "unknown")
                created_at = event.get("created_at", "")
                payload = event.get("payload", {})
                
                # Форматируем событие
                message_text += f"📌 {event_type}\n"
                message_text += f"   📅 {created_at}\n"
                if payload:
                    message_text += f"   📝 {str(payload)[:50]}...\n"
                message_text += "\n"
        
        await message.answer(
            text=message_text,
            reply_markup=get_back_keyboard("main")
        )
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        await message.answer(
            text=f"❌ Квитанция №{receipt_number} не найдена или ошибка при получении истории.\n\n"
                 f"Проверьте номер и попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
    
    await state.clear()
