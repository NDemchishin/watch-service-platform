"""
Обработчики для ОТК.
Согласно ТЗ п. 7: ОТК и возвраты.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import OTK
from telegram_bot.keyboards.main_menu import get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:otk")
async def start_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало работы с ОТК."""
    await callback.message.edit_text(
        text="🔍 ОТК\n\n"
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
    
    try:
        receipt = await api_client.get_receipt_by_number(receipt_number)
        
        await state.update_data(
            receipt_id=receipt.get("id"),
            receipt_number=receipt_number
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 Просмотр истории", callback_data="otk:history"),
                ],
                [
                    InlineKeyboardButton(text="↩️ Оформить возврат", callback_data="otk:return"),
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back:main"),
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
        logger.error(f"Error finding receipt: {e}")
        await message.answer(
            text=f"❌ Квитанция №{receipt_number} не найдена.\n\n"
                 f"Проверьте номер и попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(OTK.select_action, F.data == "otk:history")
async def show_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать историю квитанции."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")
    receipt_id = data.get("receipt_id")
    
    try:
        history = await api_client.get_receipt_history(receipt_id)
        
        if not history:
            message_text = f"📜 История квитанции №{receipt_number}\n\nИстория пуста."
        else:
            message_text = f"📜 История квитанции №{receipt_number}\n\n"
            for event in history:
                event_type = event.get("event_type", "unknown")
                created_at = event.get("created_at", "")
                message_text += f"• {event_type} - {created_at}\n"
        
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_back_keyboard("main")
        )
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении истории.",
            reply_markup=get_back_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(OTK.select_action, F.data == "otk:return")
async def start_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало оформления возврата."""
    # Получаем причины возврата
    try:
        reasons = await api_client.get_return_reasons()
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for reason in reasons:
            buttons.append([
                InlineKeyboardButton(
                    text=reason.get("name", "Unknown"),
                    callback_data=f"reason:{reason.get('id')}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu:otk")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text="↩️ Оформление возврата\n\n"
                 "Выберите причину возврата:",
            reply_markup=keyboard
        )
        await state.set_state(OTK.select_return_reasons)
        
    except Exception as e:
        logger.error(f"Error fetching return reasons: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении причин возврата.",
            reply_markup=get_back_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(OTK.select_return_reasons, F.data.startswith("reason:"))
async def select_return_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор причины возврата."""
    reason_id = int(callback.data.split(":")[1])
    
    # Получаем информацию о причине
    try:
        reasons = await api_client.get_return_reasons()
        selected_reason = next((r for r in reasons if r.get("id") == reason_id), None)
        
        await state.update_data(
            reason_id=reason_id,
            reason_name=selected_reason.get("name", "Unknown")
        )
        
        # Если причина = полировка, спрашиваем кто виноват
        if selected_reason and "полировка" in selected_reason.get("name", "").lower():
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Полировщик", callback_data="resp:polisher"),
                        InlineKeyboardButton(text="Сборщик", callback_data="resp:assembler"),
                    ],
                    [
                        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:otk"),
                    ],
                ]
            )
            
            await callback.message.edit_text(
                text="↩️ Кто несет ответственность?",
                reply_markup=keyboard
            )
            await state.set_state(OTK.select_responsible)
        else:
            # Для других причин сразу подтверждаем
            data = await state.get_data()
            await callback.message.edit_text(
                text=f"↩️ Подтверждение возврата\n\n"
                     f"Квитанция: №{data.get('receipt_number')}\n"
                     f"Причина: {selected_reason.get('name', 'Unknown')}\n\n"
                     f"Подтвердите:",
                reply_markup=get_confirm_keyboard()
            )
            await state.set_state(OTK.confirm_return)
        
    except Exception as e:
        logger.error(f"Error processing return reason: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при обработке причины возврата.",
            reply_markup=get_back_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(OTK.select_responsible, F.data.startswith("resp:"))
async def select_responsible(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор ответственного (для полировки)."""
    responsible = callback.data.split(":")[1]  # polisher или assembler
    await state.update_data(responsible=responsible)
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        text=f"↩️ Подтверждение возврата\n\n"
             f"Квитанция: №{data.get('receipt_number')}\n"
             f"Причина: {data.get('reason_name')}\n"
             f"Ответственный: {'Полировщик' if responsible == 'polisher' else 'Сборщик'}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(OTK.confirm_return)
    await callback.answer()


@router.callback_query(OTK.confirm_return, F.data == "confirm")
async def confirm_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение возврата."""
    data = await state.get_data()
    
    try:
        # Создаем возврат через API
        return_data = await api_client.create_return(
            receipt_id=data.get("receipt_id"),
            reason_id=data.get("reason_id"),
            responsible=data.get("responsible")
        )
        
        await callback.message.edit_text(
            text="✅ Возврат успешно оформлен!",
            reply_markup=get_back_keyboard("main")
        )
        logger.info(f"Return created: {return_data}")
        
    except Exception as e:
        logger.error(f"Error creating return: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при оформлении возврата.",
            reply_markup=get_back_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()
