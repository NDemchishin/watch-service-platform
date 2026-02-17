"""
Обработчики для управления сотрудниками.
Согласно ТЗ Sprint 3: добавление, активация, деактивация сотрудников.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Employees
from telegram_bot.keyboards.main_menu import (
    get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard,
    get_confirmation_keyboard,
)
from telegram_bot.services.api_client import get_api_client
from telegram_bot.utils import push_nav

logger = logging.getLogger(__name__)
router = Router()

ROLE_LABELS = {"master": "👨‍🔧 Мастер", "polisher": "🪙 Полировщик"}


@router.callback_query(F.data == "menu:employees")
async def employees_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню сотрудников."""
    await push_nav(state, "MainMenu.main", "employees_menu")
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

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍🔧 Мастер", callback_data="emp:role:master"),
            ],
            [
                InlineKeyboardButton(text="🪙 Полировщик", callback_data="emp:role:polisher"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:employees"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
            ],
        ]
    )

    await message.answer(
        text=f"👥 Выберите роль для сотрудника {name}:",
        reply_markup=keyboard,
    )
    await state.set_state(Employees.select_role)


@router.callback_query(Employees.select_role, F.data.startswith("emp:role:"))
async def process_employee_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора роли сотрудника."""
    role = callback.data.split(":")[2]  # master или polisher
    await state.update_data(role=role)

    data = await state.get_data()
    role_label = ROLE_LABELS.get(role, role)

    await callback.message.edit_text(
        text=f"👥 Подтверждение добавления сотрудника\n\n"
             f"ФИО: {data.get('name')}\n"
             f"Роль: {role_label}\n\n"
             f"Подтвердите:",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(Employees.add_employee)
    await callback.answer()


@router.callback_query(Employees.add_employee, F.data == "confirm")
async def confirm_add_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение добавления сотрудника."""
    data = await state.get_data()

    try:
        employee = await get_api_client().create_employee(
            name=data.get("name"),
            role=data.get("role"),
        )

        role_label = ROLE_LABELS.get(employee.get("role", ""), "")

        await callback.message.edit_text(
            text=f"✅ Сотрудник добавлен!\n\n"
                 f"ID: {employee.get('id')}\n"
                 f"Имя: {employee.get('name')}\n"
                 f"Роль: {role_label}",
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
            role_icon = "👨‍🔧" if emp.get("role") == "master" else "🪙"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {role_icon} {emp.get('name')}",
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

        new_role = "polisher" if employee.get("role") == "master" else "master"
        new_role_label = "🪙 Сделать полировщиком" if new_role == "polisher" else "👨‍🔧 Сделать мастером"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=action_text, callback_data=action_callback),
                ],
                [
                    InlineKeyboardButton(text=new_role_label, callback_data=f"emp:change_role:{employee_id}:{new_role}"),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="emp:list_all"),
                    InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
                ],
            ]
        )

        name = employee.get("name", "Unknown")
        status = "✅ Активен" if is_active else "🚫 Неактивен"
        role_label = ROLE_LABELS.get(employee.get("role", ""), "")

        await callback.message.edit_text(
            text=f"👥 {name}\n\n"
                 f"Роль: {role_label}\n"
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
async def confirm_activate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение активации сотрудника."""
    employee_id = int(callback.data.split(":")[2])

    try:
        employee = await get_api_client().get_employee(employee_id)
        name = employee.get("name", "Unknown")
        await state.update_data(pending_employee_id=employee_id, pending_employee_name=name)

        await callback.message.edit_text(
            text=f"Активировать сотрудника {name}?",
            reply_markup=get_confirmation_keyboard("activate", str(employee_id))
        )
        await state.set_state(Employees.confirm_activate)

    except Exception as e:
        logger.error(f"Error fetching employee for activation: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении данных сотрудника.",
            reply_markup=get_back_home_keyboard("employees")
        )

    await callback.answer()


@router.callback_query(Employees.confirm_activate, F.data.startswith("confirm:activate:"))
async def do_activate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнение активации после подтверждения."""
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
async def confirm_deactivate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение деактивации сотрудника."""
    employee_id = int(callback.data.split(":")[2])

    try:
        employee = await get_api_client().get_employee(employee_id)
        name = employee.get("name", "Unknown")
        await state.update_data(pending_employee_id=employee_id, pending_employee_name=name)

        await callback.message.edit_text(
            text=f"Деактивировать сотрудника {name}?",
            reply_markup=get_confirmation_keyboard("deactivate", str(employee_id))
        )
        await state.set_state(Employees.confirm_deactivate)

    except Exception as e:
        logger.error(f"Error fetching employee for deactivation: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при получении данных сотрудника.",
            reply_markup=get_back_home_keyboard("employees")
        )

    await callback.answer()


@router.callback_query(Employees.confirm_deactivate, F.data.startswith("confirm:deactivate:"))
async def do_deactivate_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнение деактивации после подтверждения."""
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


@router.callback_query(F.data.startswith("emp:change_role:"))
async def change_employee_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Смена роли сотрудника."""
    parts = callback.data.split(":")
    employee_id = int(parts[2])
    new_role = parts[3]

    try:
        updated = await get_api_client().update_employee(employee_id, role=new_role)

        role_label = ROLE_LABELS.get(new_role, new_role)
        await callback.message.edit_text(
            text=f"✅ Роль сотрудника {updated.get('name')} изменена на {role_label}!",
            reply_markup=get_back_home_keyboard("employees")
        )
        logger.info(f"Employee {employee_id} role changed to {new_role}")

    except Exception as e:
        logger.error(f"Error changing employee role: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при смене роли.",
            reply_markup=get_back_home_keyboard("employees")
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена подтверждения — возврат в меню сотрудников."""
    await employees_menu(callback, state)


@router.callback_query(F.data == "back:employees")
async def back_to_employees(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в меню сотрудников."""
    await employees_menu(callback, state)
