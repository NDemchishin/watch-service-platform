"""
Обработчики для управления сотрудниками.
Согласно ТЗ Sprint 3: добавление, активация, деактивация сотрудников.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Employees
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard
from telegram_bot.services.api_client import get_api_client


@router.callback_query(F.data == "menu:employees")
async def employees_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню сотрудников."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить сотрудника", callback_data="emp:add"),
            ],
            [
                InlineKeyboardButton(text="👥 Все сотрудники", callback_data="emp:list_all"),
            ],
            [
                InlineKeyboardButton(text="🚫 Неактивные сотрудники", callback_data="emp:list_inactive"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:main"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
            ],
        ]
    )
    
    await callback.message.edit_text(
        text="👥 Управление сотрудниками\n\n"
             "Выберите действие:",
        reply_markup=keyboard
    )
    await state.set_state(Employees.main_menu)
    await callback.answer()


@router.callback_query(F.data == "emp:add")
async def start_add_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления сотрудника."""
    await callback.message.edit_text(
        text="👥 Добавление сотрудника\n\n"
             "Введите ФИО сотрудника:",
        reply_markup=get_back_keyboard("employees")
    )
    await state.set_state(Employees.enter_name)
    await callback.answer()


@router.message(Employees.enter_name)
async def process_employee_name(message: Message, state: FSMContext) -> None:
    """Обработка ввода ФИО сотрудника."""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            text="❌ ФИО слишком короткое. Введите минимум 2 символа:",
            reply_markup=get_back_keyboard("employees")
        )
        return
    
    await state.update_data(name=name)
    
    await message.answer(
        text=f"👥 Подтверждение добавления сотрудника\n\n"
             f"ФИО: {name}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Employees.add_employee)


@router.callback_query(Employees.add_employee, F.data == "confirm")
async def confirm_add_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение добавления сотрудника."""
    data = await state.get_data()
    
    try:
        employee = await get_api_client().create_employee(
            name=data.get("name"),
        )
        
        await callback.message.edit_text(
            text=f"✅ Сотрудник добавлен!\n\n"
                 f"ID: {employee.get('id')}\n"
                 f"Имя: {employee.get('name')}",
            reply_markup=get_back_home_keyboard("employees")
        )
        logger.info(f"Employee created: {employee}")
        
    except Exception as e:
        logger.error(f"Error creating employee: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при добавлении сотрудника.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "emp:list_all")
async def list_all_employees(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает всех сотрудников."""
    try:
        employees = await get_api_client().get_all_employees()
        
        if not employees:
            await callback.message.edit_text(
                text="👥 Все сотрудники\n\nСотрудников пока нет.",
                reply_markup=get_back_home_keyboard("employees")
            )
            await callback.answer()
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            status = "✅" if emp.get("is_active", True) else "🚫"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {emp.get('name')}",
                    callback_data=f"emp:view:{emp.get('id')}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data="back:employees"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text="👥 Все сотрудники\n\n"
                 "Выберите сотрудника для активации/деактивации:",
            reply_markup=keyboard
        )
        await state.set_state(Employees.list_all)
        
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении списка сотрудников.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await callback.answer()


@router.callback_query(F.data == "emp:list_inactive")
async def list_inactive_employees(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает неактивных сотрудников."""
    try:
        employees = await get_api_client().get_inactive_employees()
        
        if not employees:
            await callback.message.edit_text(
                text="🚫 Неактивные сотрудники\n\nНет неактивных сотрудников.",
                reply_markup=get_back_home_keyboard("employees")
            )
            await callback.answer()
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            buttons.append([
                InlineKeyboardButton(
                    text=f"✅ {emp.get('name')}",
                    callback_data=f"emp:activate:{emp.get('id')}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data="back:employees"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text="🚫 Неактивные сотрудники\n\n"
                 "Нажмите на сотрудника для активации:",
            reply_markup=keyboard
        )
        await state.set_state(Employees.list_inactive)
        
    except Exception as e:
        logger.error(f"Error fetching inactive employees: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении списка.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("emp:view:"))
async def view_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр и управление сотрудником."""
    employee_id = int(callback.data.split(":")[2])
    
    try:
        employee = await get_api_client().get_employee(employee_id)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        is_active = employee.get("is_active", True)
        action_text = "🚫 Деактивировать" if is_active else "✅ Активировать"
        action_callback = f"emp:deactivate:{employee_id}" if is_active else f"emp:activate:{employee_id}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=action_text, callback_data=action_callback),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="emp:list_all"),
                    InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
                ],
            ]
        )
        
        name = employee.get("name", "Unknown")
        
        status = "✅ Активен" if is_active else "🚫 Неактивен"
        
        await callback.message.edit_text(
            text=f"👥 {name}\n\n"
                 f"Статус: {status}\n"
                 f"ID: {employee_id}",
            reply_markup=keyboard
        )
        await state.set_state(Employees.select_employee)
        
    except Exception as e:
        logger.error(f"Error fetching employee: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении сотрудника.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("emp:activate:"))
async def activate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Активация сотрудника."""
    employee_id = int(callback.data.split(":")[2])
    
    try:
        employee = await get_api_client().activate_employee(employee_id)
        
        await callback.message.edit_text(
            text=f"✅ Сотрудник {employee.get('name')} активирован!",
            reply_markup=get_back_home_keyboard("employees")
        )
        logger.info(f"Employee {employee_id} activated")
        
    except Exception as e:
        logger.error(f"Error activating employee: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при активации.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("emp:deactivate:"))
async def deactivate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Деактивация сотрудника."""
    employee_id = int(callback.data.split(":")[2])
    
    try:
        employee = await get_api_client().deactivate_employee(employee_id)
        
        await callback.message.edit_text(
            text=f"🚫 Сотрудник {employee.get('name')} деактивирован!",
            reply_markup=get_back_home_keyboard("employees")
        )
        logger.info(f"Employee {employee_id} deactivated")
        
    except Exception as e:
        logger.error(f"Error deactivating employee: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при деактивации.",
            reply_markup=get_back_home_keyboard("employees")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:employees")
async def back_to_employees(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в меню сотрудников."""
    await employees_menu(callback, state)
