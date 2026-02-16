"""
Состояния FSM для Telegram бота.
Согласно ТЗ: бот ведёт пользователя вопросами.
"""
from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    """Главное меню."""
    main = State()


class Master(StatesGroup):
    """Выдача часов мастеру."""
    waiting_for_receipt_number = State()
    select_master = State()
    is_urgent = State()
    enter_deadline = State()
    confirm = State()


class Polishing(StatesGroup):
    """Полировка."""
    waiting_for_receipt_number = State()
    select_polisher = State()
    enter_metal_type = State()
    has_bracelet = State()
    is_complex = State()
    enter_comment = State()
    confirm = State()


class OTK(StatesGroup):
    """ОТК и возвраты."""
    waiting_for_receipt_number = State()
    select_action = State()  # проверка или возврат
    # Для возврата
    select_return_reasons = State()
    select_responsible = State()
    confirm_return = State()


class Urgent(StatesGroup):
    """Срочные часы."""
    list = State()
    select_receipt = State()
    change_deadline = State()


class History(StatesGroup):
    """История по квитанции."""
    waiting_for_receipt_number = State()
    show_history = State()
    select_action = State()  # изменить срок, сменить мастера, добавить комментарий
    enter_new_deadline = State()
    select_new_master = State()
    enter_comment = State()


class Analytics(StatesGroup):
    """Аналитика."""
    menu = State()
    select_period = State()
    show_result = State()


class Employees(StatesGroup):
    """Управление сотрудниками."""
    main_menu = State()
    add_employee = State()
    enter_name = State()
    enter_telegram_id = State()
    list_all = State()
    list_inactive = State()
    select_employee = State()
    confirm_activate = State()
    confirm_deactivate = State()
