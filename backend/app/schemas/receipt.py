"""
Pydantic схемы для квитанций.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schemas.history import HistoryEventResponse


class ReceiptBase(BaseModel):
    """Базовая схема квитанции."""
    receipt_number: str
    current_deadline: Optional[datetime] = None


class ReceiptCreate(ReceiptBase):
    """Схема создания квитанции."""
    pass


class ReceiptGetOrCreate(BaseModel):
    """Схема для получения или создания квитанции через API."""
    receipt_number: str
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None


class ReceiptUpdate(BaseModel):
    """Схема обновления квитанции (смена дедлайна)."""
    current_deadline: Optional[datetime] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None


class AssignMasterRequest(BaseModel):
    """Схема для выдачи часов мастеру."""
    receipt_id: int
    master_id: int
    is_urgent: bool = False
    deadline: Optional[datetime] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None


class ReceiptResponse(ReceiptBase):
    """Схема ответа с данными квитанции."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


class ReceiptListResponse(BaseModel):
    """Схема списка квитанций."""
    items: list[ReceiptResponse]
    total: int
    skip: int = 0
    limit: int = 100


class ReceiptWithHistoryResponse(ReceiptResponse):
    """Схема квитанции с историей."""
    history: list["HistoryEventResponse"] = []


# Импорты для forward reference
from app.schemas.history import HistoryEventResponse

ReceiptWithHistoryResponse.model_rebuild()
