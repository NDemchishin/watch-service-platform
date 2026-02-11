"""
HTTP клиент для взаимодействия с API бэкенда.
Согласно ТЗ п. 12.2: бот работает ТОЛЬКО через FastAPI.
"""
import httpx
import logging
from typing import Optional
from datetime import datetime
from telegram_bot.config import bot_config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class APIClient:
    """Клиент для работы с API бэкенда."""
    
    _instance = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls, base_url: str = None):
        """Singleton pattern для предотвращения создания множественных соединений."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, base_url: str = None):
        """Инициализация клиента."""
        if not hasattr(self, '_initialized'):
            self.base_url = base_url or bot_config.get_api_base_url()
            # Ensure URL has protocol
            if self.base_url and not self.base_url.startswith(('http://', 'https://')):
                self.base_url = 'http://' + self.base_url
            logger.info(f"API client initialized with base URL: {self.base_url}")
            self._initialized = True
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Получает или создаёт HTTP клиент."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, 
                timeout=30.0,
                follow_redirects=True
            )
            logger.debug("Created new HTTP client")
        return self._client
    
    async def close(self):
        """Закрывает HTTP клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("HTTP client closed")
            self._client = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Выполняет HTTP запрос к API с retry логикой."""
        # Remove trailing slash from endpoint to avoid redirect issues
        endpoint = endpoint.rstrip('/')
        
        client = await self._get_client()
        
        try:
            url = f"/api/v1{endpoint}"
            logger.debug(f"Making {method} request to {url}")
            
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Connection error to {endpoint}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} on {endpoint}: {e.response.text if e.response else e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error on {endpoint}: {e}")
            raise

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
            logger.error(f"HTTP error {e.response.status_code} for receipt {receipt_number}: {e.response.text}")
            if e.response.status_code == 400:
                # Квитанция уже существует, пробуем получить
                raise ValueError(f"Квитанция с номером {receipt_number} уже существует")
            raise
        except Exception as e:
            logger.error(f"Error getting/creating receipt {receipt_number}: {e}")
            raise

    async def get_receipt_by_number(self, receipt_number: str) -> dict:
        """Получает квитанцию по номеру."""
        try:
            return await self._request("GET", f"/receipts/number/{receipt_number}")
        except httpx.HTTPStatusError:
            raise ValueError(f"Квитанция с номером {receipt_number} не найдена")

    async def get_urgent_receipts(self) -> list[dict]:
        """Получает список срочных часов (с дедлайном, не прошедших ОТК)."""
        response = await self._request("GET", "/receipts/urgent")
        return response.get("items", []) if isinstance(response, dict) else response

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
        response = await self._request(
            "GET",
            "/receipts/",
            params={"skip": skip, "limit": limit}
        )
        return response.get("items", []) if isinstance(response, dict) else response

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
        # Все параметры передаём как query-параметры
        params = {
            "receipt_id": receipt_id,
            "master_id": master_id,
            "is_urgent": is_urgent,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
        }
        if deadline:
            params["deadline"] = deadline.isoformat()
        
        return await self._request(
            "POST",
            "/receipts/assign-master",
            params=params,
        )

    # ===== Employees =====
    async def get_employees(self, active_only: bool = True) -> list[dict]:
        """Получает список сотрудников."""
        response = await self._request(
            "GET",
            "/employees/",
            params={"active_only": active_only}
        )
        return response.get("items", []) if isinstance(response, dict) else response

    async def get_all_employees(self) -> list[dict]:
        """Получает список всех сотрудников (включая неактивных)."""
        response = await self._request("GET", "/employees/")
        return response.get("items", []) if isinstance(response, dict) else response

    async def get_inactive_employees(self) -> list[dict]:
        """Получает список неактивных сотрудников."""
        response = await self._request(
            "GET",
            "/employees/",
            params={"active_only": False, "inactive_only": True}
        )
        return response.get("items", []) if isinstance(response, dict) else response

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
        response = await self._request("GET", "/returns/reasons")
        return response.get("items", []) if isinstance(response, dict) else response

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
        response = await self._request(
            "GET",
            f"/history/receipt/{receipt_id}"
        )
        return response.get("items", []) if isinstance(response, dict) else response

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


# Глобальный экземпляр клиента
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Получает глобальный экземпляр API клиента."""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


async def close_api_client():
    """Закрывает глобальный API клиент."""
    global _api_client
    if _api_client:
        await _api_client.close()
        _api_client = None
