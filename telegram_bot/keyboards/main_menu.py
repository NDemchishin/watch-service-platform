"""
Клавиатуры для Telegram бота.
Согласно ТЗ: главное меню с inline-кнопками.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню бота.
    Согласно ТЗ п. 10.2:
    📥 Новая квитанция
    🔧 Операции
    🪙 Полировка
    🔍 ОТК
    📜 История
    """
    buttons = [
        [
            InlineKeyboardButton(text="📥 Новая квитанция", callback_data="menu:new_receipt"),
        ],
        [
            InlineKeyboardButton(text="🔧 Операции", callback_data="menu:operations"),
        ],
        [
            InlineKeyboardButton(text="🪙 Полировка", callback_data="menu:polishing"),
        ],
        [
            InlineKeyboardButton(text="🔍 ОТК", callback_data="menu:otk"),
        ],
        [
            InlineKeyboardButton(text="📜 История", callback_data="menu:history"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(back_to: str = "main") -> InlineKeyboardMarkup:
    """Кнопка 'Назад' для возврата в меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"back:{back_to}")]
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены действия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
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
