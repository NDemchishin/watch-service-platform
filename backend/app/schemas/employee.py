"""
Pydantic схемы для сотрудников.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmployeeBase(BaseModel):
    """Базовая схема сотрудника."""
    name: str
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    """Схема создания сотрудника."""
    pass


class EmployeeUpdate(BaseModel):
    """Схема обновления сотрудника."""
    name: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Схема ответа с данными сотрудника."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


class EmployeeListResponse(BaseModel):
    """Схема списка сотрудников."""
    model_config = ConfigDict(from_attributes=True)
    
    items: list[EmployeeResponse]
    total: int
