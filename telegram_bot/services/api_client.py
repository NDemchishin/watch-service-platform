"""
HTTP клиент для взаимодействия с API бэкенда.
Согласно ТЗ п. 12.2: бот работает ТОЛЬКО через FastAPI.
"""
import httpx
from typing import Optional
from datetime import datetime
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
            url=f"/api/v1{endpoint}",
            params=params,
            json=json_data,
        )
        response.raise_for_status()
        return response.json()

    # ===== Receipts =====
    async def get_or_create_receipt(
        self,
        receipt_number: str,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """
        Получает квитанцию по номеру или создаёт новую.
        Согласно ТЗ: квитанция создаётся автоматически, если её нет.
        """
        try:
            return await self._request(
                "POST",
                "/receipts/get-or-create",
                json_data={
                    "receipt_number": receipt_number,
                    "telegram_id": telegram_id,
                    "telegram_username": telegram_username,
                }
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Квитанция уже существует, пробуем получить
                raise ValueError(f"Квитанция с номером {receipt_number} уже существует")
            raise

    async def get_receipt_by_number(self, receipt_number: str) -> dict:
        """Получает квитанцию по номеру."""
        try:
            return await self._request("GET", f"/receipts/number/{receipt_number}")
        except httpx.HTTPStatusError:
            raise ValueError(f"Квитанция с номером {receipt_number} не найдена")

    async def get_urgent_receipts(self) -> list[dict]:
        """Получает список срочных часов (с дедлайном, не прошедших ОТК)."""
        return await self._request("GET", "/receipts/urgent")

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

    async def get_receipts(self, skip: int = 0, limit: int = 10) -> list[dict]:
        """Получает список квитанций с пагинацией."""
        return await self._request(
            "GET",
            "/receipts/",
            params={"skip": skip, "limit": limit}
        )

    async def update_deadline(
        self,
        receipt_id: int,
        new_deadline: datetime,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Обновляет дедлайн квитанции."""
        return await self._request(
            "PATCH",
            f"/receipts/{receipt_id}/deadline",
            json_data={"current_deadline": new_deadline.isoformat()},
            params={"telegram_id": telegram_id, "telegram_username": telegram_username}
        )

    # ===== Master Assignment =====
    async def assign_to_master(
        self,
        receipt_id: int,
        master_id: int,
        is_urgent: bool = False,
        deadline: Optional[datetime] = None,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Выдаёт часы мастеру."""
        data = {
            "receipt_id": receipt_id,
            "master_id": master_id,
            "is_urgent": is_urgent,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
        }
        if deadline:
            data["deadline"] = deadline.isoformat()
        
        return await self._request(
            "POST",
            "/receipts/assign-master",
            json_data=data
        )

    # ===== Employees =====
    async def get_employees(self, active_only: bool = True) -> list[dict]:
        """Получает список сотрудников."""
        return await self._request(
            "GET", 
            "/employees/",
            params={"active_only": active_only}
        )

    async def get_all_employees(self) -> list[dict]:
        """Получает список всех сотрудников (включая неактивных)."""
        return await self._request("GET", "/employees/")

    async def get_inactive_employees(self) -> list[dict]:
        """Получает список неактивных сотрудников."""
        return await self._request(
            "GET",
            "/employees/",
            params={"active_only": False, "inactive_only": True}
        )

    async def create_employee(
        self,
        name: str,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> dict:
        """Создаёт нового сотрудника."""
        return await self._request(
            "POST",
            "/employees/",
            json_data={
                "name": name,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
            }
        )

    async def activate_employee(self, employee_id: int) -> dict:
        """Активирует сотрудника."""
        return await self._request(
            "POST",
            f"/employees/{employee_id}/activate"
        )

    async def deactivate_employee(self, employee_id: int) -> dict:
        """Деактивирует сотрудника."""
        return await self._request(
            "POST",
            f"/employees/{employee_id}/deactivate"
        )

    async def get_employee(self, employee_id: int) -> dict:
        """Получает сотрудника по ID."""
        return await self._request("GET", f"/employees/{employee_id}")

    # ===== Operations =====
    async def create_operation(
        self,
        receipt_id: int,
        employee_id: int,
        operation_type: str,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Создает операцию."""
        return await self._request(
            "POST",
            "/operations/",
            json_data={
                "receipt_id": receipt_id,
                "employee_id": employee_id,
                "operation_type": operation_type,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
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
        comment: str = "",
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Создает запись о полировке."""
        return await self._request(
            "POST",
            "/polishing/",
            json_data={
                "receipt_id": receipt_id,
                "polisher_id": polisher_id,
                "metal_type": metal_type,
                "bracelet": has_bracelet,
                "difficult": is_complex,
                "comment": comment,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
            }
        )

    # ===== OTK =====
    async def otk_pass(
        self,
        receipt_id: int,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Отмечает прохождение ОТК."""
        return await self._request(
            "POST",
            f"/receipts/{receipt_id}/otk-pass",
            json_data={
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
            }
        )

    async def initiate_return(
        self,
        receipt_id: int,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Инициирует возврат (заглушка для Sprint 3)."""
        return await self._request(
            "POST",
            f"/receipts/{receipt_id}/initiate-return",
            json_data={
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
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
        responsible: Optional[str] = None,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Создает возврат."""
        data = {
            "receipt_id": receipt_id,
            "reason_id": reason_id,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
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

    async def add_history_event(
        self,
        receipt_id: int,
        event_type: str,
        payload: dict = None,
        telegram_id: int = None,
        telegram_username: str = None,
    ) -> dict:
        """Добавляет событие в историю."""
        return await self._request(
            "POST",
            "/history/",
            json_data={
                "receipt_id": receipt_id,
                "event_type": event_type,
                "payload": payload,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
            }
        )
