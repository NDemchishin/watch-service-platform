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


class ReceiptUpdate(BaseModel):
    """Схема обновления квитанции (смена дедлайна)."""
    current_deadline: Optional[datetime] = None


class ReceiptResponse(ReceiptBase):
    """Схема ответа с данными квитанции."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


class ReceiptListResponse(BaseModel):
    """Схема списка квитанций."""
    items: list[ReceiptResponse]
    total: int


class ReceiptWithHistoryResponse(ReceiptResponse):
    """Схема квитанции с историей."""
    history: list["HistoryEventResponse"] = []


# Импорты для forward reference
from app.schemas.history import HistoryEventResponse

ReceiptWithHistoryResponse.model_rebuild()
