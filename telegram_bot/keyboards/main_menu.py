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
        [
            InlineKeyboardButton(text="📊 Аналитика", callback_data="menu:analytics"),
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


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения/отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ]
        ]
    )


def get_optional_input_keyboard(field: str, back_to: str) -> InlineKeyboardMarkup:
    """Клавиатура для необязательного поля: Пропустить / Назад / В меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{field}")],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data=f"back:{back_to}"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
            ],
        ]
    )


def get_confirmation_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия с ID объекта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{item_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"),
            ]
        ]
    )
