"""
Обработчики для списка срочных часов.
Согласно ТЗ Sprint 3: показ часов с дедлайном, изменение дедлайна.
"""
import logging
import httpx
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Urgent
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard
from telegram_bot.services.api_client import get_api_client
from telegram_bot.services.notification_scheduler import send_notification_to_otk, NOTIFICATION_MESSAGES
from telegram_bot.utils import format_datetime, push_nav

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:urgent")
async def show_urgent_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список срочных часов."""
    await push_nav(state, "MainMenu.main", "show_urgent_list")
    try:
        receipts = await get_api_client().get_urgent_receipts()
        
        if not receipts:
            await callback.message.edit_text(
                text="🕒 Срочные часы\n\n"
                     "Нет срочных часов.",
                reply_markup=get_back_home_keyboard("main")
            )
            await callback.answer()
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for receipt in receipts:
            deadline_str = format_datetime(
                receipt.get("current_deadline"), fmt="%d.%m %H:%M"
            )
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"🕒 №{receipt.get('receipt_number')} — {deadline_str}",
                    callback_data=f"urgent:view:{receipt.get('id')}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data="back:main"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text="🕒 Срочные часы\n\n"
                 "Выберите квитанцию для изменения срока:",
            reply_markup=keyboard
        )
        await state.set_state(Urgent.list)
        
    except httpx.ConnectError:
        logger.exception("Connection error while fetching urgent receipts")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while fetching urgent receipts")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при получении списка.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching urgent receipts: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при получении списка.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("urgent:view:"))
async def view_urgent_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр срочной квитанции."""
    receipt_id = int(callback.data.split(":")[2])
    
    try:
        receipt = await get_api_client().get_receipt(receipt_id)
        history = await get_api_client().get_receipt_history(receipt_id)
        
        deadline_str = format_datetime(receipt.get("current_deadline"))
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить срок",
                        callback_data=f"urgent:edit:{receipt_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(text="📜 История", callback_data=f"urgent:history:{receipt_id}"),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="back:urgent"),
                    InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
                ],
            ]
        )
        
        # Формируем краткую информацию
        receipt_number = receipt.get("receipt_number", "Unknown")
        
        message_text = f"🕒 Квитанция №{receipt_number}\n\n"
        message_text += f"📅 Срок готовности: {deadline_str}\n"
        message_text += f"📋 Всего событий в истории: {len(history)}\n"
        
        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard
        )
        await state.set_state(Urgent.select_receipt)
        
    except httpx.ConnectError:
        logger.exception("Connection error while fetching receipt")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while fetching receipt")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при получении квитанции.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching receipt: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при получении квитанции.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("urgent:edit:"))
async def start_edit_deadline(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало изменения дедлайна."""
    receipt_id = int(callback.data.split(":")[2])
    await state.update_data(receipt_id=receipt_id)
    
    await callback.message.edit_text(
        text="🕒 Введите новую дату и время готовности\n\n"
             "Введите в формате: ДД.ММ ЧЧ:ММ\n"
             "Например: 15.01 14:30",
        reply_markup=get_back_keyboard("urgent")
    )
    await state.set_state(Urgent.change_deadline)
    await callback.answer()


@router.message(Urgent.change_deadline)
async def process_new_deadline(message: Message, state: FSMContext) -> None:
    """Обработка нового дедлайна."""
    text = message.text.strip()
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    user = message.from_user
    
    try:
        # Парсим дату и время
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
        
        # Создаём datetime
        now = datetime.utcnow()
        new_deadline = now.replace(
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )
        
        # Если дата уже прошла, считаем что это следующий год
        if new_deadline < now:
            new_deadline = new_deadline.replace(year=now.year + 1)
        
        # Получаем квитанцию для номера
        receipt = await get_api_client().get_receipt(receipt_id)
        receipt_number = receipt.get("receipt_number", str(receipt_id))
        old_deadline_raw = receipt.get("current_deadline")
        old_deadline_str = format_datetime(old_deadline_raw) if old_deadline_raw else "не установлен"

        # Обновляем дедлайн через API
        await get_api_client().update_deadline(
            receipt_id=receipt_id,
            new_deadline=new_deadline,
            telegram_id=user.id,
            telegram_username=user.username,
        )

        await message.answer(
            text=f"✅ Срок успешно изменён!\n\n"
                 f"Новая дата: {new_deadline.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Deadline updated for receipt {receipt_id}")

        # Отправляем уведомление всем OTK (Issue #26)
        notify_text = NOTIFICATION_MESSAGES["deadline_changed"].format(
            receipt_number=receipt_number,
            old_deadline=old_deadline_str,
            new_deadline=new_deadline.strftime("%d.%m.%Y %H:%M"),
            username=user.username or str(user.id),
        )
        await send_notification_to_otk(message.bot, notify_text)
        
    except ValueError as e:
        logger.error(f"Error parsing deadline: {e}")
        await message.answer(
            text="❌ Неверный формат.\n\n"
                 "Введите в формате: ДД.ММ ЧЧ:ММ\n"
                 "Например: 15.01 14:30",
            reply_markup=get_back_keyboard("urgent")
        )
        return
    except Exception as e:
        logger.error(f"Error updating deadline: {e}")
        await message.answer(
            text="❌ Ошибка при изменении срока.",
            reply_markup=get_back_home_keyboard("urgent")
        )

    await state.clear()


@router.callback_query(F.data.startswith("urgent:history:"))
async def show_urgent_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает историю квитанции."""
    receipt_id = int(callback.data.split(":")[2])
    
    try:
        receipt = await get_api_client().get_receipt(receipt_id)
        history = await get_api_client().get_receipt_history(receipt_id)
        
        receipt_number = receipt.get("receipt_number", "Unknown")
        
        if not history:
            message_text = f"📜 История квитанции №{receipt_number}\n\nИстория пуста."
        else:
            message_text = f"📜 История квитанции №{receipt_number}\n\n"
            for event in history:
                event_type = event.get("event_type", "unknown")
                created_at = event.get("created_at", "")
                message_text += f"• {event_type} - {created_at[:16]}\n"
        
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_back_home_keyboard("urgent")
        )

    except httpx.ConnectError:
        logger.exception("Connection error while fetching history")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("urgent")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while fetching history")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при получении истории.",
            reply_markup=get_back_home_keyboard("urgent")
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching history: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при получении истории.",
            reply_markup=get_back_home_keyboard("urgent")
        )

    await callback.answer()


@router.callback_query(F.data == "back:urgent")
async def back_to_urgent(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к списку срочных часов."""
    await show_urgent_list(callback, state)
