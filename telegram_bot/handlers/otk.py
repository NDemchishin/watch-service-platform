"""
Обработчики для ОТК.
Согласно ТЗ Sprint 3: ОТК-проверка с кнопками "Часы готовы" и "Оформить возврат".
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import OTK
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:otk")
async def start_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало работы с ОТК."""
    await callback.message.edit_text(
        text="🔍 ОТК-проверка\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(OTK.waiting_for_receipt_number)
    await callback.answer()


@router.message(OTK.waiting_for_receipt_number)
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
    
    user = message.from_user
    
    try:
        # Пытаемся получить или создать квитанцию
        receipt = await api_client.get_or_create_receipt(
            receipt_number=receipt_number,
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await state.update_data(
            receipt_id=receipt.get("id"),
            receipt_number=receipt_number,
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Часы готовы", callback_data="otk:pass"),
                    InlineKeyboardButton(text="🔁 Оформить возврат", callback_data="otk:return"),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="back:otk"),
                ],
            ]
        )
        
        await message.answer(
            text=f"🔍 Квитанция №{receipt_number}\n\n"
                 f"Выберите действие:",
            reply_markup=keyboard
        )
        await state.set_state(OTK.select_action)
        
    except Exception as e:
        logger.error(f"Error with receipt: {e}")
        await message.answer(
            text=f"❌ Ошибка при работе с квитанцией №{receipt_number}.\n\n"
                 f"Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(OTK.select_action, F.data == "otk:pass")
async def pass_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Часы прошли ОТК."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = callback.from_user
    
    try:
        # Отмечаем прохождение ОТК
        await api_client.otk_pass(
            receipt_id=receipt_id,
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await callback.message.edit_text(
            text=f"✅ Квитанция №{receipt_number}\n\n"
                 f"Часы успешно прошли ОТК!",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Receipt {receipt_id} passed OTK")
        
    except Exception as e:
        logger.error(f"Error passing OTK: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при отметке ОТК.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(OTK.select_action, F.data == "otk:return")
async def initiate_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Инициирует возврат (заглушка для Sprint 3)."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = callback.from_user
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔁 Оформить возврат", callback_data="otk:return:confirm"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:otk"),
            ],
        ]
    )
    
    await callback.message.edit_text(
        text=f"🔁 Квитанция №{receipt_number}\n\n"
             f"Оформление возврата (Sprint 3 - заглушка)\n\n"
             f"Будет создано событие 'return_initiated'.\n"
             f"Полная логика возвратов - Sprint 4.\n\n"
             f"Продолжить?",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(OTK.confirm_return)
    await callback.answer()


@router.callback_query(OTK.confirm_return, F.data == "confirm")
async def confirm_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение возврата."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = callback.from_user
    
    try:
        # Инициируем возврат (заглушка)
        await api_client.initiate_return(
            receipt_id=receipt_id,
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await callback.message.edit_text(
            text=f"🔁 Квитанция №{receipt_number}\n\n"
                 f"Возврат инициирован!\n\n"
                 f"Полная логика возвратов будет реализована в Sprint 4.",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Return initiated for receipt {receipt_id}")
        
    except Exception as e:
        logger.error(f"Error initiating return: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при оформлении возврата.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:otk")
async def back_to_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к началу ОТК."""
    await start_otk(callback, state)
