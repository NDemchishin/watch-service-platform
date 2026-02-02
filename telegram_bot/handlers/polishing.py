"""
Обработчики для полировки.
Согласно ТЗ Sprint 3: квитанция создаётся автоматически.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Polishing
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()


def get_api_client() -> APIClient:
    """Ленивое создание API клиента."""
    return APIClient()


@router.callback_query(F.data == "menu:polishing")
async def start_polishing(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало работы с полировкой."""
    await callback.message.edit_text(
        text="🪙 Отправить в полировку\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(Polishing.waiting_for_receipt_number)
    await callback.answer()


@router.message(Polishing.waiting_for_receipt_number)
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
        receipt = await get_api_client().get_or_create_receipt(
            receipt_number=receipt_number,
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await state.update_data(
            receipt_id=receipt.get("id"),
            receipt_number=receipt_number,
        )
        
        # Получаем список полировщиков
        employees = await get_api_client().get_employees(active_only=True)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            buttons.append([
                InlineKeyboardButton(
                    text=emp.get("name", "Unknown"),
                    callback_data=f"polisher:{emp.get('id')}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:polishing")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            text=f"🪙 Квитанция №{receipt_number}\n\n"
                 f"Выберите полировщика:",
            reply_markup=keyboard
        )
        await state.set_state(Polishing.select_polisher)
        
    except Exception as e:
        logger.error(f"Error with receipt: {e}")
        await message.answer(
            text=f"❌ Ошибка при работе с квитанцией №{receipt_number}.\n\n"
                 f"Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(Polishing.select_polisher, F.data.startswith("polisher:"))
async def select_polisher(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор полировщика."""
    polisher_id = int(callback.data.split(":")[1])
    await state.update_data(polisher_id=polisher_id)
    
    await callback.message.edit_text(
        text="🪙 Тип металла\n\n"
             "Введите тип металла (например: сталь, золото, платина):",
        reply_markup=get_back_keyboard("polishing")
    )
    await state.set_state(Polishing.enter_metal_type)
    await callback.answer()


@router.message(Polishing.enter_metal_type)
async def process_metal_type(message: Message, state: FSMContext) -> None:
    """Обработка ввода типа металла."""
    metal_type = message.text.strip()
    if not metal_type:
        await message.answer(
            text="❌ Введите тип металла:",
            reply_markup=get_back_keyboard("polishing")
        )
        return
    
    await state.update_data(metal_type=metal_type)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="bracelet:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="bracelet:no"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:polishing"),
            ],
        ]
    )
    
    await message.answer(
        text="🪙 Браслет\n\n"
             "Есть браслет для полировки?",
        reply_markup=keyboard
    )
    await state.set_state(Polishing.has_bracelet)


@router.callback_query(Polishing.has_bracelet, F.data.startswith("bracelet:"))
async def process_bracelet(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка наличия браслета."""
    has_bracelet = callback.data.split(":")[1] == "yes"
    await state.update_data(has_bracelet=has_bracelet)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="complex:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="complex:no"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:polishing"),
            ],
        ]
    )
    
    await callback.message.edit_text(
        text="🪙 Сложность\n\n"
             "Сложная полировка?",
        reply_markup=keyboard
    )
    await state.set_state(Polishing.is_complex)
    await callback.answer()


@router.callback_query(Polishing.is_complex, F.data.startswith("complex:"))
async def process_complex(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка сложности полировки."""
    is_complex = callback.data.split(":")[1] == "yes"
    await state.update_data(is_complex=is_complex)
    
    await callback.message.edit_text(
        text="🪙 Комментарий\n\n"
             "Введите комментарий (или отправьте '-' если не нужен):",
        reply_markup=get_back_keyboard("polishing")
    )
    await state.set_state(Polishing.enter_comment)
    await callback.answer()


@router.message(Polishing.enter_comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    """Обработка комментария."""
    comment = message.text.strip()
    if comment == "-":
        comment = ""
    
    await state.update_data(comment=comment)
    
    data = await state.get_data()
    
    await message.answer(
        text=f"🪙 Подтверждение передачи в полировку\n\n"
             f"Квитанция: №{data.get('receipt_number')}\n"
             f"Металл: {data.get('metal_type')}\n"
             f"Браслет: {'Да' if data.get('has_bracelet') else 'Нет'}\n"
             f"Сложная: {'Да' if data.get('is_complex') else 'Нет'}\n"
             f"Комментарий: {comment or '-'}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Polishing.confirm)


@router.callback_query(Polishing.confirm, F.data == "confirm")
async def confirm_polishing(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение передачи в полировку."""
    data = await state.get_data()
    user = callback.from_user
    
    try:
        # Создаем запись о полировке через API
        polishing = await get_api_client().create_polishing(
            receipt_id=data.get("receipt_id"),
            polisher_id=data.get("polisher_id"),
            metal_type=data.get("metal_type"),
            has_bracelet=data.get("has_bracelet"),
            is_complex=data.get("is_complex"),
            comment=data.get("comment"),
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await callback.message.edit_text(
            text="✅ Часы переданы в полировку!",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Polishing created for receipt {data.get('receipt_id')}")
        
    except Exception as e:
        logger.error(f"Error creating polishing: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при передаче в полировку.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:polishing")
async def back_to_polishing(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к началу полировки."""
    await start_polishing(callback, state)
