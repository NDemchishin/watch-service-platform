"""
Обработчики для ОТК.
Sprint 4: полный flow возвратов с выбором причин и атрибуцией виновного.
"""
import logging
import httpx
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from telegram_bot.states import OTK
from telegram_bot.keyboards.main_menu import get_back_home_keyboard, get_back_keyboard
from telegram_bot.services.api_client import get_api_client
from telegram_bot.utils import push_nav

logger = logging.getLogger(__name__)
router = Router()

# Код причины, при которой нужно спрашивать виновного
POLISHING_REASON_CODE = "polishing"


@router.callback_query(F.data == "menu:otk")
async def start_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало работы с ОТК."""
    await push_nav(state, "MainMenu.main", "start_otk")
    await state.set_state(OTK.waiting_for_receipt_number)
    await callback.message.edit_text(
        text="🔍 ОТК-проверка\n\n"
             "Введите номер квитанции:",
        reply_markup=get_back_keyboard("main")
    )
    await callback.answer()


@router.message(OTK.waiting_for_receipt_number)
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

    user = message.from_user

    try:
        receipt = await get_api_client().get_or_create_receipt(
            receipt_number=receipt_number,
            telegram_id=user.id,
            telegram_username=user.username,
        )

        await state.update_data(
            receipt_id=receipt.get("id"),
            receipt_number=receipt_number,
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Часы готовы", callback_data="otk:pass"),
                    InlineKeyboardButton(text="🔁 Оформить возврат", callback_data="otk:return"),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="back:otk"),
                ],
            ]
        )

        await push_nav(state, "OTK.waiting_for_receipt_number", "process_receipt_number")
        await message.answer(
            text=f"🔍 Квитанция №{receipt_number}\n\n"
                 f"Выберите действие:",
            reply_markup=keyboard
        )
        await state.set_state(OTK.select_action)

    except httpx.ConnectError:
        logger.exception("Connection error while processing receipt for OTK")
        await message.answer(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} for receipt {receipt_number}")
        await message.answer(
            text=f"❌ Ошибка сервера при работе с квитанцией №{receipt_number}.\n\n"
                 f"Попробуйте снова:",
            reply_markup=get_back_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error with receipt for OTK: {e}")
        await message.answer(
            text="❌ Непредвиденная ошибка. Попробуйте снова.",
            reply_markup=get_back_keyboard("main")
        )


@router.callback_query(OTK.select_action, F.data == "otk:pass")
async def pass_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Часы прошли ОТК."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    user = callback.from_user

    try:
        await get_api_client().otk_pass(
            receipt_id=receipt_id,
            telegram_id=user.id,
            telegram_username=user.username,
        )

        await callback.message.edit_text(
            text=f"✅ Квитанция №{receipt_number}\n\n"
                 f"Часы успешно прошли ОТК!",
            reply_markup=get_back_home_keyboard("main")
        )
        logger.info(f"Receipt {receipt_id} passed OTK")

    except httpx.ConnectError:
        logger.exception("Connection error while passing OTK")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while passing OTK")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при отметке ОТК.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error passing OTK: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при отметке ОТК.",
            reply_markup=get_back_home_keyboard("main")
        )

    await state.clear()
    await callback.answer()


# ===== Возврат: выбор причин (Issue #19) =====


@router.callback_query(OTK.select_action, F.data == "otk:return")
async def start_return_reasons(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает выбор причин возврата."""
    try:
        reasons = await get_api_client().get_return_reasons()
        await state.update_data(
            available_reasons=reasons,
            selected_reason_ids=[],
        )
        await _show_reasons_keyboard(callback, state, reasons, [])
        await state.set_state(OTK.select_return_reasons)

    except httpx.ConnectError:
        logger.exception("Connection error while fetching return reasons")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Error fetching return reasons: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке причин возврата.",
            reply_markup=get_back_home_keyboard("main")
        )

    await callback.answer()


async def _show_reasons_keyboard(
    callback: CallbackQuery,
    state: FSMContext,
    reasons: list[dict],
    selected_ids: list[int],
) -> None:
    """Показывает клавиатуру выбора причин с галочками."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")

    buttons = []
    for reason in reasons:
        rid = reason["id"]
        name = reason["name"]
        check = "✅ " if rid in selected_ids else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{check}{name}",
                callback_data=f"otk:reason:{rid}",
            )
        ])

    # Кнопка "Готово" — только если выбрана хотя бы одна причина
    if selected_ids:
        buttons.append([
            InlineKeyboardButton(text="✔️ Готово", callback_data="otk:reasons_done"),
        ])

    buttons.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="back:otk_action"),
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    selected_count = len(selected_ids)
    await callback.message.edit_text(
        text=f"🔁 Возврат квитанции №{receipt_number}\n\n"
             f"Выберите причины возврата (выбрано: {selected_count}):",
        reply_markup=keyboard,
    )


@router.callback_query(OTK.select_return_reasons, F.data.startswith("otk:reason:"))
async def toggle_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключает выбор причины (toggle)."""
    reason_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    selected = data.get("selected_reason_ids", [])
    reasons = data.get("available_reasons", [])

    if reason_id in selected:
        selected.remove(reason_id)
    else:
        selected.append(reason_id)

    await state.update_data(selected_reason_ids=selected)
    await _show_reasons_keyboard(callback, state, reasons, selected)
    await callback.answer()


@router.callback_query(OTK.select_return_reasons, F.data == "otk:reasons_done")
async def reasons_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Причины выбраны — проверяем, нужна ли атрибуция виновного."""
    data = await state.get_data()
    selected_ids = data.get("selected_reason_ids", [])
    reasons = data.get("available_reasons", [])

    # Проверяем: есть ли среди выбранных причина "полировка"
    has_polishing = any(
        r["code"] == POLISHING_REASON_CODE
        for r in reasons
        if r["id"] in selected_ids
    )

    if has_polishing:
        # Issue #20: спрашиваем, чья вина
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🪙 Полировщик",
                        callback_data="otk:guilty_role:polisher",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="👨‍🔧 Сборщик",
                        callback_data="otk:guilty_role:assembler",
                    ),
                ],
                [
                    InlineKeyboardButton(text="⬅ Назад", callback_data="otk:back_to_reasons"),
                ],
            ]
        )
        receipt_number = data.get("receipt_number")
        await callback.message.edit_text(
            text=f"🔁 Возврат квитанции №{receipt_number}\n\n"
                 f"Причина возврата — полировка.\n"
                 f"Чья вина?",
            reply_markup=keyboard,
        )
        await state.set_state(OTK.select_responsible)
    else:
        # Нет причины "полировка" — переходим к подтверждению
        await _show_return_confirmation(callback, state)

    await callback.answer()


# ===== Атрибуция виновного (Issue #20) =====


@router.callback_query(OTK.select_responsible, F.data.startswith("otk:guilty_role:"))
async def select_guilty_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрана роль виновного — показываем список сотрудников."""
    role = callback.data.split(":")[2]  # polisher или assembler
    await state.update_data(guilty_role=role)

    try:
        employees = await get_api_client().get_employees(active_only=True)
        data = await state.get_data()
        receipt_number = data.get("receipt_number")

        role_name = "полировщика" if role == "polisher" else "сборщика"

        buttons = []
        for emp in employees:
            buttons.append([
                InlineKeyboardButton(
                    text=emp.get("name", "???"),
                    callback_data=f"otk:guilty:{emp.get('id')}",
                )
            ])

        buttons.append([
            InlineKeyboardButton(text="⬅ Назад", callback_data="otk:back_to_reasons"),
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            text=f"🔁 Возврат квитанции №{receipt_number}\n\n"
                 f"Выберите виновного {role_name}:",
            reply_markup=keyboard,
        )

    except httpx.ConnectError:
        logger.exception("Connection error while fetching employees for guilty selection")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Error fetching employees for guilty: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке списка сотрудников.",
            reply_markup=get_back_home_keyboard("main")
        )

    await callback.answer()


@router.callback_query(OTK.select_responsible, F.data.startswith("otk:guilty:"))
async def select_guilty_employee(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбран конкретный виновный сотрудник."""
    guilty_id = int(callback.data.split(":")[2])
    # Extract employee name from the button text
    guilty_name = callback.data.split(":")[2]
    if callback.message and callback.message.reply_markup:
        for row in callback.message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data == callback.data:
                    guilty_name = btn.text
                    break
    await state.update_data(guilty_employee_id=guilty_id, guilty_employee_name=guilty_name)
    await _show_return_confirmation(callback, state)
    await callback.answer()


@router.callback_query(OTK.select_responsible, F.data == "otk:back_to_reasons")
@router.callback_query(OTK.select_return_reasons, F.data == "otk:back_to_reasons")
async def back_to_reasons(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад к выбору причин."""
    data = await state.get_data()
    reasons = data.get("available_reasons", [])
    selected = data.get("selected_reason_ids", [])
    # Сбрасываем данные виновного
    await state.update_data(guilty_employee_id=None, guilty_role=None)
    await _show_reasons_keyboard(callback, state, reasons, selected)
    await state.set_state(OTK.select_return_reasons)
    await callback.answer()


# ===== Подтверждение и создание возврата (Issue #21) =====


async def _show_return_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает экран подтверждения возврата."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")
    selected_ids = data.get("selected_reason_ids", [])
    reasons = data.get("available_reasons", [])
    guilty_id = data.get("guilty_employee_id")

    # Собираем текст причин
    reason_names = [r["name"] for r in reasons if r["id"] in selected_ids]
    reasons_text = "\n".join(f"  • {name}" for name in reason_names)

    text = (
        f"🔁 Возврат квитанции №{receipt_number}\n\n"
        f"Причины:\n{reasons_text}\n"
    )

    if guilty_id:
        role = data.get("guilty_role", "")
        role_name = "Полировщик" if role == "polisher" else "Сборщик"
        guilty_name = data.get("guilty_employee_name", f"ID {guilty_id}")
        text += f"\nВиновный ({role_name}): {guilty_name}\n"

    text += "\nПодтвердить возврат?"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="otk:return:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ],
        ]
    )

    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await state.set_state(OTK.confirm_return)


@router.callback_query(OTK.confirm_return, F.data == "otk:return:confirm")
async def confirm_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение возврата — создаём Return через API."""
    data = await state.get_data()
    receipt_id = data.get("receipt_id")
    receipt_number = data.get("receipt_number")
    selected_ids = data.get("selected_reason_ids", [])
    available_reasons = data.get("available_reasons", [])
    guilty_id = data.get("guilty_employee_id")
    user = callback.from_user

    # Формируем список причин для API
    reasons_payload = []
    for reason in available_reasons:
        if reason["id"] in selected_ids:
            reason_data = {"reason_id": reason["id"]}
            # Виновного назначаем только для причины "полировка"
            if reason["code"] == POLISHING_REASON_CODE and guilty_id:
                reason_data["guilty_employee_id"] = guilty_id
            reasons_payload.append(reason_data)

    try:
        await get_api_client().create_return(
            receipt_id=receipt_id,
            reasons=reasons_payload,
            telegram_id=user.id,
            telegram_username=user.username,
        )

        # Issue #22: спрашиваем про ещё один возврат
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔁 Ещё один возврат",
                        callback_data="otk:another_return",
                    ),
                ],
                [
                    InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main"),
                ],
            ]
        )

        reason_names = [r["name"] for r in available_reasons if r["id"] in selected_ids]
        reasons_text = ", ".join(reason_names)

        await callback.message.edit_text(
            text=f"✅ Возврат оформлен!\n\n"
                 f"Квитанция №{receipt_number}\n"
                 f"Причины: {reasons_text}\n\n"
                 f"Оформить ещё один возврат на эту квитанцию?",
            reply_markup=keyboard,
        )
        logger.info(f"Return created for receipt {receipt_id}, reasons: {selected_ids}")

    except httpx.ConnectError:
        logger.exception("Connection error while creating return")
        await callback.message.edit_text(
            text="❌ Сервер недоступен. Попробуйте позже.",
            reply_markup=get_back_home_keyboard("main")
        )
    except httpx.HTTPStatusError as e:
        logger.exception(f"HTTP error {e.response.status_code} while creating return")
        await callback.message.edit_text(
            text="❌ Ошибка сервера при оформлении возврата.",
            reply_markup=get_back_home_keyboard("main")
        )
    except Exception as e:
        logger.exception(f"Unexpected error creating return: {e}")
        await callback.message.edit_text(
            text="❌ Непредвиденная ошибка при оформлении возврата.",
            reply_markup=get_back_home_keyboard("main")
        )

    await callback.answer()


# ===== Ещё один возврат (Issue #22) =====


@router.callback_query(F.data == "otk:another_return")
async def another_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Оформление ещё одного возврата на ту же квитанцию."""
    # Сбрасываем данные о причинах, но оставляем receipt_id/number
    data = await state.get_data()
    await state.update_data(
        selected_reason_ids=[],
        guilty_employee_id=None,
        guilty_role=None,
    )

    try:
        reasons = await get_api_client().get_return_reasons()
        await state.update_data(available_reasons=reasons)
        await _show_reasons_keyboard(callback, state, reasons, [])
        await state.set_state(OTK.select_return_reasons)

    except Exception as e:
        logger.exception(f"Error starting another return: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке причин возврата.",
            reply_markup=get_back_home_keyboard("main")
        )

    await callback.answer()


# ===== Отмена и навигация =====


@router.callback_query(OTK.confirm_return, F.data == "cancel")
async def cancel_return(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена возврата."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")

    await callback.message.edit_text(
        text=f"❌ Возврат отменён.\n\nКвитанция №{receipt_number}",
        reply_markup=get_back_home_keyboard("main")
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back:otk_action")
async def back_to_otk_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад к выбору действия (Часы готовы / Оформить возврат)."""
    data = await state.get_data()
    receipt_number = data.get("receipt_number")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Часы готовы", callback_data="otk:pass"),
                InlineKeyboardButton(text="🔁 Оформить возврат", callback_data="otk:return"),
            ],
            [
                InlineKeyboardButton(text="⬅ Назад", callback_data="back:otk"),
            ],
        ]
    )

    await callback.message.edit_text(
        text=f"🔍 Квитанция №{receipt_number}\n\n"
             f"Выберите действие:",
        reply_markup=keyboard,
    )
    await state.set_state(OTK.select_action)
    await callback.answer()


@router.callback_query(F.data == "back:otk")
async def back_to_otk(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к началу ОТК."""
    await start_otk(callback, state)
