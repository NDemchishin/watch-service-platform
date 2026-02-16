"""
Тесты хендлеров бота (Issue #18).
Используем мок API-клиента, без реальных запросов.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import CallbackQuery, Message, User, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey


def make_user(user_id=123, username="testuser") -> User:
    """Создаёт мок-пользователя Telegram."""
    return User(id=user_id, is_bot=False, first_name="Test", username=username)


def make_chat(chat_id=123) -> Chat:
    """Создаёт мок-чат."""
    return Chat(id=chat_id, type="private")


def make_callback(data: str, user_id=123, message_text="test") -> CallbackQuery:
    """Создаёт мок CallbackQuery."""
    user = make_user(user_id)
    chat = make_chat(user_id)

    message = MagicMock()
    message.chat = chat
    message.from_user = user
    message.text = message_text
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()

    callback = MagicMock(spec=CallbackQuery)
    callback.data = data
    callback.from_user = user
    callback.message = message
    callback.answer = AsyncMock()

    return callback


def make_message(text: str, user_id=123) -> Message:
    """Создаёт мок Message."""
    user = make_user(user_id)
    chat = make_chat(user_id)

    message = MagicMock(spec=Message)
    message.text = text
    message.from_user = user
    message.chat = chat
    message.answer = AsyncMock()
    message.bot = MagicMock()

    return message


@pytest.fixture
def state():
    """Создаёт FSMContext для тестов."""
    storage = MemoryStorage()
    key = StorageKey(chat_id=123, user_id=123, bot_id=1)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def mock_api():
    """Мок API-клиента — патчим во всех handler модулях где используется."""
    api = AsyncMock()
    patches = [
        patch("telegram_bot.handlers.urgent.get_api_client", return_value=api),
        patch("telegram_bot.handlers.history.get_api_client", return_value=api),
        patch("telegram_bot.handlers.master.get_api_client", return_value=api),
        patch("telegram_bot.handlers.otk.get_api_client", return_value=api),
        patch("telegram_bot.services.api_client.get_api_client", return_value=api),
    ]
    for p in patches:
        p.start()
    yield api
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
def allow_all_users():
    """Разрешаем всех пользователей для тестов."""
    with patch("telegram_bot.config.bot_config.is_allowed", return_value=True):
        yield


class TestMenuHandler:
    """Тесты обработки главного меню."""

    @pytest.mark.asyncio
    async def test_menu_start(self, state, mock_api):
        from telegram_bot.handlers.menu import show_main_menu

        callback = make_callback("menu:main")
        await show_main_menu(callback, state)

        callback.message.edit_text.assert_called_once()
        call_text = str(callback.message.edit_text.call_args)
        assert "Выберите действие" in call_text or "действие" in call_text.lower()


class TestMasterFlow:
    """Тесты назначения мастера."""

    @pytest.mark.asyncio
    async def test_master_start(self, state, mock_api):
        """Начало flow назначения мастера - запрос номера квитанции."""
        from telegram_bot.handlers.master import start_master

        callback = make_callback("menu:master")
        await start_master(callback, state)

        callback.message.edit_text.assert_called_once()
        call_text = str(callback.message.edit_text.call_args)
        assert "квитанц" in call_text.lower() or "номер" in call_text.lower()


class TestOTKFlow:
    """Тесты прохождения ОТК."""

    @pytest.mark.asyncio
    async def test_otk_start(self, state, mock_api):
        """Начало OTK flow."""
        from telegram_bot.handlers.otk import start_otk

        callback = make_callback("menu:otk")
        await start_otk(callback, state)

        callback.message.edit_text.assert_called_once()


class TestUrgentFlow:
    """Тесты срочных часов."""

    @pytest.mark.asyncio
    async def test_urgent_list_empty(self, state, mock_api):
        """Пустой список срочных часов."""
        mock_api.get_urgent_receipts.return_value = []

        from telegram_bot.handlers.urgent import show_urgent_list

        callback = make_callback("menu:urgent")
        await show_urgent_list(callback, state)

        callback.message.edit_text.assert_called_once()
        call_text = str(callback.message.edit_text.call_args)
        assert "Нет срочных" in call_text or "срочн" in call_text.lower()

    @pytest.mark.asyncio
    async def test_urgent_list_with_items(self, state, mock_api):
        """Список с элементами."""
        mock_api.get_urgent_receipts.return_value = [
            {"id": 1, "receipt_number": "R-001", "current_deadline": "2025-12-31T15:00:00"},
        ]

        from telegram_bot.handlers.urgent import show_urgent_list

        callback = make_callback("menu:urgent")
        await show_urgent_list(callback, state)

        callback.message.edit_text.assert_called_once()


class TestHistoryFlow:
    """Тесты просмотра истории."""

    @pytest.mark.asyncio
    async def test_history_start(self, state, mock_api):
        """Начало flow истории."""
        from telegram_bot.handlers.history import start_history

        callback = make_callback("menu:history")
        await start_history(callback, state)

        callback.message.edit_text.assert_called_once()
