"""
HTTP клиент для взаимодействия с API бэкенда.
Согласно ТЗ п. 12.2: бот работает ТОЛЬКО через FastAPI.
"""
import httpx
from typing import Optional
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
    async def create_receipt(self, receipt_number: str) -> dict:
        """Создает новую квитанцию."""
        return await self._request(
            "POST",
            "/receipts/",
            json_data={"receipt_number": receipt_number}
        )

    async def get_receipt(self, receipt_id: int) -> dict:
        """Получает квитанцию по ID."""
        return await self._request("GET", f"/receipts/{receipt_id}")

    async def get_receipt_by_number(self, receipt_number: str) -> dict:
        """Получает квитанцию по номеру."""
        # Поиск через список с фильтром
        receipts = await self._request(
            "GET",
            "/receipts/",
            params={"receipt_number": receipt_number}
        )
        if receipts and len(receipts) > 0:
            return receipts[0]
        raise ValueError(f"Receipt with number {receipt_number} not found")

    async def get_receipts(self, skip: int = 0, limit: int = 10) -> list[dict]:
        """Получает список квитанций с пагинацией."""
        return await self._request(
            "GET",
            "/receipts/",
            params={"skip": skip, "limit": limit}
        )

    # ===== Employees =====
    async def get_employees(self) -> list[dict]:
        """Получает список сотрудников."""
        return await self._request("GET", "/employees/")

    # ===== Operations =====
    async def create_operation(
        self,
        receipt_id: int,
        employee_id: int,
        operation_type: str
    ) -> dict:
        """Создает операцию."""
        return await self._request(
            "POST",
            "/operations/",
            json_data={
                "receipt_id": receipt_id,
                "employee_id": employee_id,
                "operation_type": operation_type
            }
        )

    # ===== Polishing =====
    async def create_polishing(
        self,
        receipt_id: int,
        polisher_id: int,
        metal_type: str,
        has_bracelet: bool,
        is_complex: bool,
        comment: str = ""
    ) -> dict:
        """Создает запись о полировке."""
        return await self._request(
            "POST",
            "/polishing/",
            json_data={
                "receipt_id": receipt_id,
                "polisher_id": polisher_id,
                "metal_type": metal_type,
                "has_bracelet": has_bracelet,
                "is_complex": is_complex,
                "comment": comment
            }
        )

    # ===== Returns =====
    async def get_return_reasons(self) -> list[dict]:
        """Получает список причин возврата."""
        return await self._request("GET", "/returns/reasons")

    async def create_return(
        self,
        receipt_id: int,
        reason_id: int,
        responsible: Optional[str] = None
    ) -> dict:
        """Создает возврат."""
        data = {
            "receipt_id": receipt_id,
            "reason_id": reason_id
        }
        if responsible:
            data["responsible"] = responsible
        
        return await self._request(
            "POST",
            "/returns/",
            json_data=data
        )

    # ===== History =====
    async def get_receipt_history(self, receipt_id: int) -> list[dict]:
        """Получает историю квитанции."""
        return await self._request(
            "GET",
            f"/history/receipt/{receipt_id}"
        )
