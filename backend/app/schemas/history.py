"""
Pydantic схемы для истории событий.
"""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict


class HistoryEventBase(BaseModel):
    """Базовая схема события истории."""
    receipt_id: int
    event_type: str
    payload: Optional[dict[str, Any]] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None


class HistoryEventCreate(HistoryEventBase):
    """Схема создания события истории."""
    pass


class HistoryEventResponse(HistoryEventBase):
    """Схема ответа с данными события истории."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


class HistoryEventListResponse(BaseModel):
    """Схема списка событий истории."""
    items: list[HistoryEventResponse]
    total: int
