"""
Клавиатуры для Telegram бота.
Согласно ТЗ: главное меню с inline-кнопками.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню бота.
    Согласно ТЗ Sprint 3:
    👨‍🔧 Выдать часы мастеру
    🪙 Отправить в полировку
    🔍 ОТК-проверка
    🕒 Срочные часы
    📜 История по квитанции
    👥 Сотрудники
    """
    buttons = [
        [
            InlineKeyboardButton(text="👨‍🔧 Выдать часы мастеру", callback_data="menu:master"),
        ],
        [
            InlineKeyboardButton(text="🪙 Отправить в полировку", callback_data="menu:polishing"),
        ],
        [
            InlineKeyboardButton(text="🔍 ОТК-проверка", callback_data="menu:otk"),
        ],
        [
            InlineKeyboardButton(text="🕒 Срочные часы", callback_data="menu:urgent"),
        ],
        [
            InlineKeyboardButton(text="📜 История по квитанции", callback_data="menu:history"),
        ],
        [
            InlineKeyboardButton(text="👥 Сотрудники", callback_data="menu:employees"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(back_to: str = "main") -> InlineKeyboardMarkup:
    """Кнопка 'Назад' для возврата в меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{back_to}")]
        ]
    )


def get_home_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'В меню'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main")]
        ]
    )


def get_back_home_keyboard(back_to: str = "main") -> InlineKeyboardMarkup:
    """Кнопки 'Назад' и 'В меню'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{back_to}"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
            ]
        ]
    )
