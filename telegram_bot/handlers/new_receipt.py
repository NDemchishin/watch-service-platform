"""
Обработчики для создания новой квитанции.
Согласно ТЗ п. 4.1: номер квитанции вводится вручную, уникален.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import NewReceipt
from telegram_bot.keyboards.main_menu import get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:new_receipt")
async def start_new_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало создания новой квитанции."""
    await callback.message.edit_text(
        text="📥 Создание новой квитанции\n\n"
             "Введите номер квитанции (только цифры):",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(NewReceipt.waiting_for_number)
    await callback.answer()


@router.message(NewReceipt.waiting_for_number)
async def process_receipt_number(message: Message, state: FSMContext) -> None:
    """Обработка ввода номера квитанции."""
    receipt_number = message.text.strip()
    
    # Проверяем, что введены только цифры
    if not receipt_number.isdigit():
        await message.answer(
            text="❌ Номер квитанции должен содержать только цифры.\n\n"
                 "Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
        return
    
    # Сохраняем номер в состоянии
    await state.update_data(receipt_number=receipt_number)
    
    # Показываем подтверждение
    await message.answer(
        text=f"📥 Создание новой квитанции\n\n"
             f"Номер квитанции: {receipt_number}\n\n"
             f"Подтвердите создание:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(NewReceipt.confirm_creation)


@router.callback_query(NewReceipt.confirm_creation, F.data == "confirm")
async def confirm_create_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение создания квитанции."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")
    
    try:
        # Создаем квитанцию через API
        receipt = await api_client.create_receipt(receipt_number=receipt_number)
        
        await callback.message.edit_text(
            text=f"✅ Квитанция №{receipt_number} успешно создана!\n\n"
                 f"ID: {receipt.get('id')}\n"
                 f"Дата создания: {receipt.get('created_at')}",
            reply_markup=get_back_keyboard("main")
        )
        logger.info(f"Receipt {receipt_number} created successfully")
        
    except Exception as e:
        logger.error(f"Error creating receipt: {e}")
        await callback.message.edit_text(
            text=f"❌ Ошибка при создании квитанции №{receipt_number}.\n\n"
                 f"Возможно, квитанция с таким номером уже существует.",
            reply_markup=get_back_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()
