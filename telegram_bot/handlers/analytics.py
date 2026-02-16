"""
Обработчики аналитики в Telegram боте.
Согласно Issue #33: отображение аналитики из Sprint 6.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from telegram_bot.states import Analytics
from telegram_bot.keyboards.main_menu import get_back_keyboard
from telegram_bot.services.api_client import get_api_client

logger = logging.getLogger(__name__)
router = Router()

PERIOD_LABELS = {
    "day": "За сегодня",
    "week": "За неделю",
    "month": "За месяц",
    "all": "За всё время",
}


def _analytics_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура подменю аналитики."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Качество сборки", callback_data="analytics:assembly")],
            [InlineKeyboardButton(text="⚙️ Качество механизма", callback_data="analytics:mechanism")],
            [InlineKeyboardButton(text="✨ Качество полировки", callback_data="analytics:polishing")],
            [InlineKeyboardButton(text="📋 Загрузка полировщиков", callback_data="analytics:workload")],
            [InlineKeyboardButton(text="📈 Производительность", callback_data="analytics:performance")],
            [InlineKeyboardButton(text="↩️ Сводка возвратов", callback_data="analytics:returns")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="menu:main")],
        ]
    )


def _period_kb(action: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора периода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data=f"aperiod:{action}:day")],
            [InlineKeyboardButton(text="Неделя", callback_data=f"aperiod:{action}:week")],
            [InlineKeyboardButton(text="Месяц", callback_data=f"aperiod:{action}:month")],
            [InlineKeyboardButton(text="Всё время", callback_data=f"aperiod:{action}:all")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="analytics:menu")],
        ]
    )


def _back_to_analytics_kb() -> InlineKeyboardMarkup:
    """Кнопка 'назад к аналитике'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ К аналитике", callback_data="analytics:menu")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main")],
        ]
    )


# ---- Вход в подменю аналитики ----

@router.callback_query(F.data == "menu:analytics")
async def show_analytics_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать подменю аналитики."""
    await callback.message.edit_text(
        text="📊 Аналитика\n\nВыберите раздел:",
        reply_markup=_analytics_menu_kb(),
    )
    await state.set_state(Analytics.menu)
    await callback.answer()


@router.callback_query(F.data == "analytics:menu")
async def back_to_analytics_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в подменю аналитики."""
    await show_analytics_menu(callback, state)


# ---- Выбор раздела → выбор периода ----

@router.callback_query(F.data.in_({
    "analytics:assembly",
    "analytics:mechanism",
    "analytics:polishing",
    "analytics:performance",
    "analytics:returns",
}))
async def select_period(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор периода для раздела аналитики."""
    action = callback.data.split(":")[1]
    labels = {
        "assembly": "🔧 Качество сборки",
        "mechanism": "⚙️ Качество механизма",
        "polishing": "✨ Качество полировки",
        "performance": "📈 Производительность",
        "returns": "↩️ Сводка возвратов",
    }
    await callback.message.edit_text(
        text=f"{labels[action]}\n\nВыберите период:",
        reply_markup=_period_kb(action),
    )
    await state.set_state(Analytics.select_period)
    await callback.answer()


# ---- Загрузка полировщиков (без периода) ----

@router.callback_query(F.data == "analytics:workload")
async def show_workload(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать загрузку полировщиков."""
    api = get_api_client()
    try:
        data = await api.get_polishing_workload()
    except Exception as e:
        logger.error(f"Error fetching polishing workload: {e}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке данных.",
            reply_markup=_back_to_analytics_kb(),
        )
        await callback.answer()
        return

    polishers = data.get("polishers", [])
    if not polishers:
        text = "📋 Загрузка полировщиков\n\nНет данных."
    else:
        lines = ["📋 Загрузка полировщиков\n"]
        for p in polishers:
            lines.append(
                f"👤 {p['employee_name']}\n"
                f"  В работе: {p['in_progress']} | Завершено: {p['completed']}\n"
                f"  Часов всего: {p['total_hours']}\n"
                f"  Сложные: {p['difficult_count']} | Простые: {p['simple_count']}\n"
                f"  С браслетом: {p['with_bracelet']} | Без: {p['without_bracelet']}\n"
                f"  Среднее время: {p['avg_hours'] or '—'} ч."
            )
        text = "\n".join(lines)

    await callback.message.edit_text(text=text, reply_markup=_back_to_analytics_kb())
    await state.set_state(Analytics.show_result)
    await callback.answer()


# ---- Обработка выбора периода → показ данных ----

@router.callback_query(F.data.startswith("aperiod:"))
async def show_analytics_data(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать данные аналитики для выбранного периода."""
    parts = callback.data.split(":")
    action = parts[1]
    period = parts[2]

    api = get_api_client()
    period_label = PERIOD_LABELS.get(period, period)

    try:
        if action == "assembly":
            text = await _format_assembly(api, period, period_label)
        elif action == "mechanism":
            text = await _format_mechanism(api, period, period_label)
        elif action == "polishing":
            text = await _format_polishing(api, period, period_label)
        elif action == "performance":
            text = await _format_performance(api, period, period_label)
        elif action == "returns":
            text = await _format_returns(api, period, period_label)
        else:
            text = "Неизвестный раздел."
    except Exception as e:
        logger.error(f"Error fetching analytics {action}: {e}")
        text = "❌ Ошибка при загрузке данных."

    await callback.message.edit_text(text=text, reply_markup=_back_to_analytics_kb())
    await state.set_state(Analytics.show_result)
    await callback.answer()


# ---- Форматирование данных ----

async def _format_assembly(api, period: str, period_label: str) -> str:
    data = await api.get_assembly_quality(period)
    employees = data.get("employees", [])
    if not employees:
        return f"🔧 Качество сборки ({period_label})\n\nНет данных."
    lines = [f"🔧 Качество сборки ({period_label})\n"]
    for e in employees:
        lines.append(
            f"👤 {e['employee_name']}\n"
            f"  Собрано: {e['total_operations']} | Возвраты: {e['total_returns']}\n"
            f"  Качество: {e['quality_percent']}%"
        )
    return "\n".join(lines)


async def _format_mechanism(api, period: str, period_label: str) -> str:
    data = await api.get_mechanism_quality(period)
    employees = data.get("employees", [])
    if not employees:
        return f"⚙️ Качество механизма ({period_label})\n\nНет данных."
    lines = [f"⚙️ Качество механизма ({period_label})\n"]
    for e in employees:
        lines.append(
            f"👤 {e['employee_name']}\n"
            f"  Ремонтов: {e['total_operations']} | Возвраты: {e['total_returns']}\n"
            f"  Качество: {e['quality_percent']}%"
        )
    return "\n".join(lines)


async def _format_polishing(api, period: str, period_label: str) -> str:
    data = await api.get_polishing_quality(period)
    polishers = data.get("polishers", [])
    if not polishers:
        return f"✨ Качество полировки ({period_label})\n\nНет данных."
    lines = [f"✨ Качество полировки ({period_label})\n"]
    for p in polishers:
        lines.append(
            f"👤 {p['employee_name']}\n"
            f"  Полировок: {p['total_polished']} | Возвраты: {p['total_returns']}\n"
            f"  Качество: {p['quality_percent']}%"
        )
    return "\n".join(lines)


async def _format_performance(api, period: str, period_label: str) -> str:
    data = await api.get_performance(period)
    employees = data.get("employees", [])
    lines = [
        f"📈 Производительность ({period_label})\n",
        f"Всего операций: {data.get('total_operations', 0)}",
        f"  Сборка: {data.get('total_assembly', 0)}",
        f"  Механизм: {data.get('total_mechanism', 0)}",
        f"  Полировка: {data.get('total_polishing', 0)}\n",
    ]
    if employees:
        lines.append("По сотрудникам:")
        for e in employees:
            lines.append(
                f"👤 {e['employee_name']}: "
                f"{e['total_count']} "
                f"(сб:{e['assembly_count']} мех:{e['mechanism_count']} пол:{e['polishing_count']})"
            )
    else:
        lines.append("Нет данных по сотрудникам.")
    return "\n".join(lines)


async def _format_returns(api, period: str, period_label: str) -> str:
    data = await api.get_returns_summary(period)
    total = data.get("total_returns", 0)
    lines = [f"↩️ Сводка возвратов ({period_label})\n", f"Всего возвратов: {total}\n"]

    by_reason = data.get("by_reason", [])
    if by_reason:
        lines.append("По причинам:")
        for r in by_reason:
            lines.append(f"  • {r['reason_name']}: {r['count']}")

    top_employees = data.get("top_employees", [])
    if top_employees:
        lines.append("\nТоп сотрудников по возвратам:")
        for i, e in enumerate(top_employees[:5], 1):
            lines.append(f"  {i}. {e['employee_name']}: {e['total_returns']}")

    if not by_reason and not top_employees:
        lines.append("Нет данных.")
    return "\n".join(lines)
