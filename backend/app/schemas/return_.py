"""
Pydantic схемы для возвратов.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schemas.employee import EmployeeResponse


class ReturnReasonBase(BaseModel):
    """Базовая схема причины возврата."""
    code: str
    name: str
    affects: str  # assembly / mechanism / polishing


class ReturnReasonResponse(ReturnReasonBase):
    """Схема ответа с причиной возврата."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class ReturnReasonListResponse(BaseModel):
    """Схема списка причин возврата."""
    items: list[ReturnReasonResponse]
    total: int


class ReturnReasonLinkCreate(BaseModel):
    """Схема создания связи возврата с причиной."""
    reason_id: int
    guilty_employee_id: Optional[int] = None


class ReturnReasonLinkResponse(BaseModel):
    """Схема ответа со связью возврата и причины."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    return_id: int
    reason_id: int
    guilty_employee_id: Optional[int] = None
    reason: Optional[ReturnReasonResponse] = None
    guilty_employee: Optional["EmployeeResponse"] = None


class ReturnBase(BaseModel):
    """Базовая схема возврата."""
    receipt_id: int
    comment: Optional[str] = None


class ReturnCreate(ReturnBase):
    """Схема создания возврата."""
    reasons: list[ReturnReasonLinkCreate]


class ReturnResponse(ReturnBase):
    """Схема ответа с данными возврата."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    reasons: list[ReturnReasonLinkResponse] = []


class ReturnListResponse(BaseModel):
    """Схема списка возвратов."""
    items: list[ReturnResponse]
    total: int
    skip: int = 0
    limit: int = 100


# Обновляем forward reference
from app.schemas.employee import EmployeeResponse

ReturnReasonLinkResponse.model_rebuild()
ReturnResponse.model_rebuild()
