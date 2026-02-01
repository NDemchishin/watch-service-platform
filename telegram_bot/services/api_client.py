"""
HTTP клиент для взаимодействия с API бэкенда.
"""
import httpx
from typing import Optional, Any
from telegram_bot.config import bot_config


class APIClient:
    """Клиент для работы с API бэкенда."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or bot_config.API_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self):
        """Закрывает HTTP клиент."""
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Выполняет HTTP запрос к API."""
        response = await self.client.request(
            method=method,
            url=f"/api{endpoint}",
            params=params,
            json=json_data,
        )
        response.raise_for_status()
        return response.json()

    # ===== Receipts =====
    async def get_receipts(self, skip: int = 0, limit: int = 10) -> list[dict]:
        """Получает список квитанций с пагинацией."""
        return await self._request("GET", "/receipts/", params={"skip": skip, "limit": limit})

    async def get_receipt(self, receipt_id: int) -> dict:
        """Получает детали квитанции по ID."""
        return await self._request("GET", f"/receipts/{receipt_id}") </think> <|tool_calls_section_begin|> <|tool_call_begin|> functions.update_todo_list:9 <|tool_call_argument_begin|> {
