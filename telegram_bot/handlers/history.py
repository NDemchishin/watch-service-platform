"""
Обработчики для просмотра истории.
Согласно ТЗ Sprint 3: история с возможностью редактирования.
"""
import logging
import httpx
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.states import History
from telegram_bot.keyboards.main_menu import (
    get_back_home_keyboard, get_back_keyboard, get_confirm_keyboard,
    get_optional_input_keyboard,
)
from telegram_bot.services.api_client import get_api_client
from telegram_bot.services.notification_scheduler import send_notification_to_otk, NOTIFICATION_MESSAGES
from telegram_bot.utils import format_datetime, push_nav

logger = logging.getLogger(__name__)
router = Router()

# Человекочитаемые названия типов событий
EVENT_TYPE_LABELS = {
    "receipt_created": "Квитанция создана",
    "sent_to_master": "Выдано мастеру",
    "deadline_changed": "Дедлайн изменён",
    "passed_otk": "Прошло ОТК",
    "return_initiated": "Возврат инициирован",
    "return_created": "Возврат оформлен",
    "polishing_sent": "Отправлено в полировку",
    "polishing_returned": "Возврат из полировки",
    "operation_created": "Операция создана",
    "master_changed": "Мастер изменён",
    "comment_added": "Комментарий",
}


def _format_event(event: dict) -> str:
    """Форматирует событие истории в читаемую строку."""
    event_type = event.get("event_type", "unknown")
    label = EVENT_TYPE_LABELS.get(event_type, event_type)
    payload = event.get("payload") or {}

    if event_type == "return_created":
        reasons = payload.get("reasons", [])
        reason_names = [r.get("reason_name", "?") for r in reasons]
        if reason_names:
            label += f" ({', '.join(reason_names)})"
        guilty_entries = [r for r in reasons if r.get("guilty_employee_name")]
        if guilty_entries:
            names = [r["guilty_employee_name"] for r in guilty_entries]
            label += f" виновный: {', '.join(names)}"

    elif event_type == "sent_to_master":
        master = payload.get("master_name")
        if master:
            label += f" — {master}"

    elif event_type == "polishing_sent":
        polisher = payload.get("polisher_name")
        if polisher:
            label += f" — {polisher}"

    elif event_type == "comment_added":
        comment = payload.get("comment", "")
        if comment:
            label += f": {comment[:40]}"

    return label


@router.callback_query(F.data == "menu:history")
async def start_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало просмотра истории."""
    await push_nav(state, "MainMenu.main", "start_history")
    await callback.message.edit_text(
        text="📜 История по квитанции\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await state.set_state(History.waiting_for_receipt_number)
    await callback.answer()


@router.message(History.waiting_for_receipt_number)
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
        receipt = await get_api_client().get_receipt_by_number(receipt_number)
        receipt_id = receipt.get("id")
        
        await state.update_data(
            receipt_id=receipt_id,
            receipt_number=receipt_number,
        )
        
        # Получаем историю
        history = await get_api_client().get_receipt_history(receipt_id)
        
        await show_history(message, state, receipt, history)
        
    except ValueError:
        await message.answer(
            text=f"❌ Квитанция №{receipt_number} не найдена.\n\n"
                 f"Проверьте номер и попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
    except httpx.ConnectError:
        logger.exception("Connection error while fetching history")
        await message.answer(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while fetching history")
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        error_text = f"❌ {detail}" if detail else "❌ Ошибка сервера при получении истории."
        await message.answer(
            text=f"{error_text}\n\nПопробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching history: {e}")
        await message.answer(
            text="❌ Непредвиденная ошибка. Попробуйте снова.",
            reply_markup=get_back_keyboard("main")
        )


async def show_history(message_or_callback, state, receipt, history) -> None:
    """Показывает историю квитанции."""
    receipt_number = receipt.get("receipt_number", "Unknown")
    receipt_id = receipt.get("id")
    
    deadline_str = format_datetime(receipt.get("current_deadline"))
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить срок", callback_data="hist:edit_deadline"),
            ],
            [
                InlineKeyboardButton(text="👨‍🔧 Сменить мастера", callback_data="hist:change_master"),
            ],
            [
                InlineKeyboardButton(text="💬 Добавить комментарий", callback_data="hist:add_comment"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:history"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
            ],
        ]
    )
    
    if not history:
        message_text = f"📜 История квитанции №{receipt_number}\n\n"
        message_text += f"📅 Дедлайн: {deadline_str}\n\n"
        message_text += "История пуста."
    else:
        message_text = f"📜 История квитанции №{receipt_number}\n\n"
        message_text += f"📅 Дедлайн: {deadline_str}\n"
        message_text += f"📊 Всего событий: {len(history)}\n\n"
        message_text += "Последние события:\n"
        
        for event in history[:10]:  # Показываем последние 10
            event_type = event.get("event_type", "unknown")
            time_str = format_datetime(event.get("created_at", ""), fmt="%d.%m %H:%M")
            label = _format_event(event)
            message_text += f"• {label} — {time_str}\n"
        
        if len(history) > 10:
            message_text += f"\n... и ещё {len(history) - 10} событий"
    
    # Проверяем тип объекта для ответа
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard
        )
        await state.set_state(History.show_history)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(
            text=message_text,
            reply_markup=keyboard
        )
        await state.set_state(History.show_history)


@router.callback_query(History.show_history, F.data == "hist:edit_deadline")
async def start_edit_deadline(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало изменения дедлайна."""
    await callback.message.edit_text(
        text="📜 Введите новую дату и время готовности\n\n"
             "Введите в формате: ДД.ММ ЧЧ:ММ\n"
             "Например: 15.01 14:30",
        reply_markup=get_back_keyboard("history")
    )
    await state.set_state(History.enter_new_deadline)
    await callback.answer()


@router.message(History.enter_new_deadline)
async def process_new_deadline(message: Message, state: FSMContext) -> None:
    """Обработка нового дедлайна."""
    text = message.text.strip()
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = message.from_user
    
    try:
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        
        date_part = parts[0]
        time_part = parts[1]
        
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
        
        now = datetime.utcnow()
        new_deadline = now.replace(
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )
        
        if new_deadline < now:
            new_deadline = new_deadline.replace(year=now.year + 1)
        
        # Получаем текущий дедлайн для уведомления
        receipt_data = await get_api_client().get_receipt(receipt_id)
        old_deadline_raw = receipt_data.get("current_deadline")
        old_deadline_str = format_datetime(old_deadline_raw) if old_deadline_raw else "не установлен"

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
            reply_markup=get_back_keyboard("history")
        )
        return
    except Exception as e:
        logger.error(f"Error updating deadline: {e}")
        await message.answer(
            text="❌ Ошибка при изменении срока.",
            reply_markup=get_back_home_keyboard("history")
        )

    await state.clear()


@router.callback_query(History.show_history, F.data == "hist:change_master")
async def start_change_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало смены мастера."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    
    try:
        employees = await get_api_client().get_employees(active_only=True)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for emp in employees:
            buttons.append([
                InlineKeyboardButton(
                    text=emp.get("name", "Unknown"),
                    callback_data=f"hist:master:{emp.get('id')}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:history")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            text="📜 Выберите нового мастера:",
            reply_markup=keyboard
        )
        await state.set_state(History.select_new_master)
        
    except httpx.ConnectError:
        logger.exception("Connection error while fetching employees")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while fetching employees")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при получении списка сотрудников.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching employees: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await callback.answer()


@router.callback_query(History.select_new_master, F.data.startswith("hist:master:"))
async def change_master(callback: CallbackQuery, state: FSMContext) -> None:
    """Смена мастера."""
    new_master_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = callback.from_user
    
    try:
        # Создаём событие истории о смене мастера
        await get_api_client().add_history_event(
            receipt_id=receipt_id,
            event_type="master_changed",
            payload={"new_master_id": new_master_id},
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await callback.message.edit_text(
            text=f"✅ Мастер изменён!\n\n"
                 f"Квитанция №{receipt_number}",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Master changed for receipt {receipt_id}")
        
    except httpx.ConnectError:
        logger.exception("Connection error while changing master")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while changing master")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при смене мастера.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error changing master: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при смене мастера.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(History.show_history, F.data == "hist:add_comment")
async def start_add_comment(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления комментария."""
    await callback.message.edit_text(
        text="📜 Введите комментарий или нажмите Пропустить:",
        reply_markup=get_optional_input_keyboard("hist_comment", "history")
    )
    await state.set_state(History.enter_comment)
    await callback.answer()


@router.callback_query(F.data == "skip:hist_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск комментария — возврат к истории."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")

    try:
        receipt = await get_api_client().get_receipt(receipt_id)
        history = await get_api_client().get_receipt_history(receipt_id)
        await show_history(callback, state, receipt, history)
    except Exception as e:
        logger.exception(f"Error returning to history after skip: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при возврате к истории.",
            reply_markup=get_back_home_keyboard("history")
        )
    await callback.answer()


@router.message(History.enter_comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    """Обработка комментария."""
    comment = message.text.strip()
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = message.from_user

    if not comment:
        await message.answer(
            text="📜 Комментарий не может быть пустым.\n\n"
                 "Введите комментарий или нажмите Пропустить:",
            reply_markup=get_optional_input_keyboard("hist_comment", "history")
        )
        return

    try:
        await get_api_client().add_history_event(
            receipt_id=receipt_id,
            event_type="comment_added",
            payload={"comment": comment},
            telegram_id=user.id,
            telegram_username=user.username,
        )
        
        await message.answer(
            text=f"✅ Комментарий добавлен!\n\n"
                 f"Квитанция №{receipt_number}",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Comment added for receipt {receipt_id}")
        
    except httpx.ConnectError:
        logger.exception("Connection error while adding comment")
        await message.answer(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while adding comment")
        await message.answer(
            text="❌ Ошибка сервера при добавлении комментария.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error adding comment: {e}")
        await message.answer(
            text="❌ Непредвиденная ошибка при добавлении комментария.",
            reply_markup=get_back_home_keyboard("main")
        )
    
    await state.clear()


@router.callback_query(F.data == "back:history")
async def back_to_history(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к вводу номера квитанции."""
    await start_history(callback, state)
