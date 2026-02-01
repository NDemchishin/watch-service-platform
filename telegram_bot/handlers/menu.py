"""
Обработчики главного меню и навигации.
Согласно ТЗ п. 10.2: бот редактирует сообщение, а не шлёт новые.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from telegram_bot.states import MainMenu
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.
    Показывает главное меню согласно ТЗ п. 10.2.
    """
    user = message.from_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для учета производства и контроля качества в часовой мастерской.\n\n"
        "Выберите действие:"
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard()
    )
    await state.set_state(MainMenu.main)


@router.callback_query(F.data == "menu:main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать главное меню (редактирование сообщения)."""
    await callback.message.edit_text(
        text="Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await state.set_state(MainMenu.main)
    await callback.answer()


@router.callback_query(F.data.startswith("back:"))
async def handle_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки 'Назад'."""
    back_to = callback.data.split(":")[1]
    
    if back_to == "main":
        await show_main_menu(callback, state)
    else:
        await callback.answer("Возврат в главное меню")
        await show_main_menu(callback, state)


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка отмены действия."""
    await state.clear()
    await callback.message.edit_text(
        text="Действие отменено.\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer("Действие отменено")
