"""
Pydantic схемы для сотрудников.
"""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict


EMPLOYEE_ROLES = ("master", "polisher")
EmployeeRole = Literal["master", "polisher"]


class EmployeeBase(BaseModel):
    """Базовая схема сотрудника."""
    name: str
    role: EmployeeRole = "master"
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    """Схема создания сотрудника."""
    role: EmployeeRole  # обязательное поле при создании, без дефолта


class EmployeeUpdate(BaseModel):
    """Схема обновления сотрудника."""
    name: Optional[str] = None
    role: Optional[EmployeeRole] = None
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
