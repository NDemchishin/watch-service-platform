"""
Тесты API-клиента бота (Issue #17).
Используем pytest-httpx или ручной мок httpx.AsyncClient.
"""
import pytest
from unittest.mock import AsyncMock
import httpx

from telegram_bot.services.api_client import APIClient


@pytest.fixture(autouse=True)
def reset_singleton():
    """Сбрасываем singleton перед каждым тестом."""
    APIClient._instance = None
    APIClient._client = None
    yield
    APIClient._instance = None
    APIClient._client = None


@pytest.fixture
def api_client():
    """Создаёт APIClient с тестовым URL."""
    client = APIClient(base_url="http://test-server:8000")
    return client


class TestSingleton:
    """Тест singleton паттерна."""

    def test_singleton_pattern(self):
        c1 = APIClient(base_url="http://test:8000")
        c2 = APIClient(base_url="http://test:8000")
        assert c1 is c2


class TestUnwrapPaginated:
    """Тест извлечения items из пагинации."""

    def test_unwrap_dict_with_items(self):
        result = APIClient._unwrap_paginated({"items": [1, 2, 3], "total": 3})
        assert result == [1, 2, 3]

    def test_unwrap_dict_without_items(self):
        result = APIClient._unwrap_paginated({"data": "value"})
        assert result == []

    def test_unwrap_list(self):
        result = APIClient._unwrap_paginated([1, 2, 3])
        assert result == [1, 2, 3]


class TestAPIRequests:
    """Тесты API запросов с моками."""

    @pytest.mark.asyncio
    async def test_get_receipt(self, api_client):
        mock_response = httpx.Response(
            200,
            json={"id": 1, "receipt_number": "R-001", "current_deadline": None, "created_at": "2025-01-01T00:00:00"},
            request=httpx.Request("GET", "http://test-server:8000/api/v1/receipts/1"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        result = await api_client.get_receipt(1)
        assert result["id"] == 1
        assert result["receipt_number"] == "R-001"

    @pytest.mark.asyncio
    async def test_get_employees_unwrap(self, api_client):
        """Проверяет unwrap пагинации для списка сотрудников."""
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {"id": 1, "name": "Иван", "is_active": True},
                    {"id": 2, "name": "Пётр", "is_active": True},
                ],
                "total": 2,
            },
            request=httpx.Request("GET", "http://test-server:8000/api/v1/employees/"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        result = await api_client.get_employees(active_only=True)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_assign_to_master(self, api_client):
        mock_response = httpx.Response(
            200,
            json={"id": 1, "receipt_number": "R-001", "current_deadline": None, "created_at": "2025-01-01T00:00:00"},
            request=httpx.Request("POST", "http://test-server:8000/api/v1/receipts/assign-master"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        result = await api_client.assign_to_master(
            receipt_id=1,
            master_id=1,
            is_urgent=False,
            telegram_id=123,
            telegram_username="test",
        )
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx(self, api_client):
        """4xx ошибки не должны retry-иться."""
        mock_response = httpx.Response(
            404,
            json={"detail": "Not found"},
            request=httpx.Request("GET", "http://test-server:8000/api/v1/receipts/999"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await api_client.get_receipt(999)

        # Должен быть ровно 1 вызов (без retry)
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_get_urgent_receipts(self, api_client):
        mock_response = httpx.Response(
            200,
            json={"items": [{"id": 1, "receipt_number": "R-001"}], "total": 1},
            request=httpx.Request("GET", "http://test-server:8000/api/v1/receipts/urgent"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        result = await api_client.get_urgent_receipts()
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_return_reasons(self, api_client):
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {"id": 1, "code": "dirt_inside", "name": "Грязь внутри", "affects": "assembly"},
                ],
                "total": 1,
            },
            request=httpx.Request("GET", "http://test-server:8000/api/v1/returns/reasons"),
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)
        api_client._client = mock_client

        result = await api_client.get_return_reasons()
        assert isinstance(result, list)
        assert result[0]["code"] == "dirt_inside"
