"""
Pydantic схемы для операций.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schemas.employee import EmployeeResponse


class OperationTypeBase(BaseModel):
    """Базовая схема типа операции."""
    code: str
    name: str


class OperationTypeResponse(OperationTypeBase):
    """Схема ответа с типом операции."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class OperationTypeListResponse(BaseModel):
    """Схема списка типов операций."""
    items: list[OperationTypeResponse]
    total: int


class OperationBase(BaseModel):
    """Базовая схема операции."""
    receipt_id: int
    operation_type_id: int
    employee_id: int


class OperationCreate(OperationBase):
    """Схема создания операции."""
    pass


class OperationResponse(OperationBase):
    """Схема ответа с данными операции."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    operation_type: Optional[OperationTypeResponse] = None
    employee: Optional["EmployeeResponse"] = None


class OperationListResponse(BaseModel):
    """Схема списка операций."""
    items: list[OperationResponse]
    total: int


# Обновляем forward reference
from app.schemas.employee import EmployeeResponse

OperationResponse.model_rebuild()
