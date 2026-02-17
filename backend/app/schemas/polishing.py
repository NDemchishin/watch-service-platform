"""
Pydantic схемы для полировки.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schemas.employee import EmployeeResponse


class PolishingDetailsBase(BaseModel):
    """Базовая схема деталей полировки."""
    receipt_id: int
    polisher_id: int
    metal_type: str
    bracelet: bool = False
    difficult: bool = False
    comment: Optional[str] = None


class PolishingDetailsCreate(PolishingDetailsBase):
    """Схема создания записи о полировке."""
    pass


class PolishingDetailsUpdate(BaseModel):
    """Схема обновления записи о полировке (возврат)."""
    returned_at: datetime


class PolishingDetailsResponse(PolishingDetailsBase):
    """Схема ответа с данными полировки."""
    model_config = ConfigDict(from_attributes=True)
    
    sent_at: datetime
    returned_at: Optional[datetime] = None
    polisher: Optional["EmployeeResponse"] = None


class PolishingDetailsListResponse(BaseModel):
    """Схема списка записей о полировке."""
    items: list[PolishingDetailsResponse]
    total: int
    skip: int = 0
    limit: int = 100


class PolishingStatsResponse(BaseModel):
    """Схема статистики по полировщику."""
    polisher_id: int
    polisher_name: str
    in_progress: int  # сколько в работе
    completed_today: int
    completed_week: int
    completed_month: int


# Обновляем forward reference
from app.schemas.employee import EmployeeResponse

PolishingDetailsResponse.model_rebuild()
