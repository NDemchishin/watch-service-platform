"""
Обработчики для выдачи часов мастеру.
Согласно ТЗ Sprint 3: квитанция создаётся автоматически, фиксация who/what/when.
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Master
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:master")
async def start_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало выдачи часов мастеру."""
    await callback.message.edit_text(
        text="👨‍🔧 Выдать часы мастеру\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(Master.waiting_for_receipt_number)
    await callback.answer()


@router.message(Master.waiting_for_receipt_number)
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
        
        # Получаем список активных сотрудников (мастеров)
        employees = await api_client.get_employees(active_only=True)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            buttons.append([
                InlineKeyboardButton(
                    text=emp.get("name", "Unknown"),
                    callback_data=f"master:{emp.get('id')}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:master")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            text=f"👨‍🔧 Квитанция №{receipt_number}\n\n"
                 f"Выберите мастера:",
            reply_markup=keyboard
        )
        await state.set_state(Master.select_master)
        
    except Exception as e:
        logger.error(f"Error with receipt: {e}")
        await message.answer(
            text=f"❌ Ошибка при работе с квитанцией №{receipt_number}.\n\n"
                 f"Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(Master.select_master, F.data.startswith("master:"))
async def select_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор мастера."""
    master_id = int(callback.data.split(":")[1])
    await state.update_data(master_id=master_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Да", callback_data="urgent:yes"),
                InlineKeyboardButton(text="⚪ Нет", callback_data="urgent:no"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:master"),
            ],
        ]
    )
    
    await callback.message.edit_text(
        text="👨‍🔧 Срочные часы?\n\n"
             "Часы срочные?",
        reply_markup=keyboard
    )
    await state.set_state(Master.is_urgent)
    await callback.answer()


@router.callback_query(Master.is_urgent, F.data.startswith("urgent:"))
async def process_urgent(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка ответа о срочности."""
    is_urgent = callback.data.split(":")[1] == "yes"
    await state.update_data(is_urgent=is_urgent)
    
    if is_urgent:
        await callback.message.edit_text(
            text="👨‍🔧 Введите дату и время готовности\n\n"
                 "Введите в формате: ДД.ММ ЧЧ:ММ\n"
                 "Например: 15.01 14:30",
            reply_markup=get_back_keyboard("master")
        )
        await state.set_state(Master.enter_deadline)
    else:
        await show_confirmation(callback, state)
    
    await callback.answer()


@router.message(Master.enter_deadline)
async def process_deadline(message: Message, state: FSMContext) -> None:
    """Обработка ввода дедлайна."""
    text = message.text.strip()
    
    try:
        # Парсим дату и время
        # Формат: ДД.ММ ЧЧ:ММ
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        
        date_part = parts[0]  # ДД.ММ
        time_part = parts[1]  # ЧЧ:ММ
        
        date_parts = date_part.split(".")
        if len(date_parts) != 2:
            raise ValueError("Неверный формат даты")
        
        day = int(date_parts[0])
        month = int(date_parts[1])
        
        time_parts = time_part.split(":")
        if len(time_parts) != 2:
            raise ValueError("Неверный формат времени")
        
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        # Создаём datetime для текущего года
        now = datetime.utcnow()
        deadline = now.replace(
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )
        
        # Если дата уже прошла в этом году, считаем что это следующий год
        if deadline < now:
            deadline = deadline.replace(year=now.year + 1)
        
        await state.update_data(deadline=deadline)
        await show_deadline_confirmation(message, state, deadline)
        
    except ValueError as e:
        await message.answer(
            text="❌ Неверный формат.\n\n"
                 "Введите в формате: ДД.ММ ЧЧ:ММ\n"
                 "Например: 15.01 14:30",
            reply_markup=get_back_keyboard("master")
        )


async def show_deadline_confirmation(message: Message, state: FSMContext, deadline: datetime) -> None:
    """Показывает подтверждение с дедлайном."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")
    
    await message.answer(
        text=f"👨‍🔧 Подтверждение\n\n"
             f"Квитанция: №{receipt_number}\n"
             f"Срочные: Да\n"
             f"Готовность: {deadline.strftime('%d.%m %H:%M')}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Master.confirm)


async def show_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает экран подтверждения."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")
    
    await callback.message.edit_text(
        text=f"👨‍🔧 Подтверждение\n\n"
             f"Квитанция: №{receipt_number}\n"
             f"Срочные: Нет\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Master.confirm)


@router.callback_query(Master.confirm, F.data == "confirm")
async def confirm_assign_to_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение выдачи мастеру."""
    data = await state.get_data()
    user = callback.from_user
    
    try:
        receipt_id = data.get("receipt_id")
        master_id = data.get("master_id")
        is_urgent = data.get("is_urgent", False)
        deadline = data.get("deadline")
        
        # Выдаём часы мастеру
        result = await api_client.assign_to_master(
            receipt_id=receipt_id,
            master_id=master_id,
            is_urgent=is_urgent,
            deadline=deadline,
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await callback.message.edit_text(
            text="✅ Часы выданы мастеру!",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Assigned to master: receipt={receipt_id}, master={master_id}")
        
    except Exception as e:
        logger.error(f"Error assigning to master: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при выдаче часов мастеру.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:master")
async def back_to_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к началу."""
    await start_master(callback, state)
