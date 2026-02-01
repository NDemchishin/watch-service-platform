"""
Обработчики для операций с квитанциями.
Согласно ТЗ п. 5: работы и операции.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Operations
from telegram_bot.keyboards.main_menu import get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import APIClient

logger = logging.getLogger(__name__)
router = Router()
api_client = APIClient()


@router.callback_query(F.data == "menu:operations")
async def start_operations(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало работы с операциями."""
    await callback.message.edit_text(
        text="🔧 Операции с квитанцией\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(Operations.waiting_for_receipt_number)
    await callback.answer()


@router.message(Operations.waiting_for_receipt_number)
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
        
        await state.update_data(
            receipt_id=receipt.get("id"),
            receipt_number=receipt_number
        )
        
        # Показываем доступные типы операций
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔨 Сборка", callback_data="op:assembly"),
                ],
                [
                    InlineKeyboardButton(text="⚙️ Ремонт механизма", callback_data="op:mechanism"),
                ],
                [
                    InlineKeyboardButton(text="✨ Полировка", callback_data="op:polishing"),
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back:main"),
                ],
            ]
        )
        
        await message.answer(
            text=f"🔧 Квитанция №{receipt_number}\n\n"
                 f"Выберите тип операции:",
            reply_markup=keyboard
        )
        await state.set_state(Operations.select_operation_type)
        
    except Exception as e:
        logger.error(f"Error finding receipt: {e}")
        await message.answer(
            text=f"❌ Квитанция №{receipt_number} не найдена.\n\n"
                 f"Проверьте номер и попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(Operations.select_operation_type, F.data.startswith("op:"))
async def select_operation_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор типа операции."""
    operation_type = callback.data.split(":")[1]
    
    operation_names = {
        "assembly": "Сборка",
        "mechanism": "Ремонт механизма",
        "polishing": "Полировка",
    }
    
    await state.update_data(operation_type=operation_type)
    
    # Получаем список сотрудников
    try:
        employees = await api_client.get_employees()
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            if emp.get("is_active", True):
                buttons.append([
                    InlineKeyboardButton(
                        text=emp.get("name", "Unknown"),
                        callback_data=f"emp:{emp.get('id')}"
                    )
                ])
        
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu:operations")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text=f"🔧 Операция: {operation_names.get(operation_type, operation_type)}\n\n"
                 f"Выберите сотрудника:",
            reply_markup=keyboard
        )
        await state.set_state(Operations.select_employee)
        
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении списка сотрудников.",
            reply_markup=get_back_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(Operations.select_employee, F.data.startswith("emp:"))
async def select_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор сотрудника."""
    employee_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    operation_type = data.get("operation_type")
    receipt_number = data.get("receipt_number")
    
    await state.update_data(employee_id=employee_id)
    
    operation_names = {
        "assembly": "Сборка",
        "mechanism": "Ремонт механизма",
        "polishing": "Полировка",
    }
    
    await callback.message.edit_text(
        text=f"🔧 Подтверждение операции\n\n"
             f"Квитанция: №{receipt_number}\n"
             f"Операция: {operation_names.get(operation_type, operation_type)}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Operations.confirm_operation)
    await callback.answer()


@router.callback_query(Operations.confirm_operation, F.data == "confirm")
async def confirm_operation(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение операции."""
    data = await state.get_data()
    
    try:
        # Создаем операцию через API
        operation = await api_client.create_operation(
            receipt_id=data.get("receipt_id"),
            employee_id=data.get("employee_id"),
            operation_type=data.get("operation_type")
        )
        
        await callback.message.edit_text(
            text="✅ Операция успешно зарегистрирована!",
            reply_markup=get_back_keyboard("main")
        )
        logger.info(f"Operation created: {operation}")
        
    except Exception as e:
        logger.error(f"Error creating operation: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при регистрации операции.",
            reply_markup=get_back_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()
