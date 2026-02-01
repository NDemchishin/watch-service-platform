"""
Состояния FSM для Telegram бота.
Согласно ТЗ: бот ведёт пользователя вопросами.
"""
from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    """Главное меню."""
    main = State()


class NewReceipt(StatesGroup):
    """Создание новой квитанции."""
    waiting_for_number = State()
    confirm_creation = State()


class Operations(StatesGroup):
    """Операции с квитанцией."""
    waiting_for_receipt_number = State()
    select_operation_type = State()
    select_employee = State()
    confirm_operation = State()


class Polishing(StatesGroup):
    """Полировка."""
    waiting_for_receipt_number = State()
    select_polisher = State()
    enter_metal_type = State()
    has_bracelet = State()
    is_complex = State()
    enter_comment = State()
    confirm_polishing = State()


class OTK(StatesGroup):
    """ОТК и возвраты."""
    waiting_for_receipt_number = State()
    select_action = State()  # проверка или возврат
    # Для возврата
    select_return_reasons = State()
    select_responsible = State()
    confirm_return = State()


class History(StatesGroup):
    """История по квитанции."""
    waiting_for_receipt_number = State()
    show_history = State()
