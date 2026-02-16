"""
Pydantic схемы для аналитики.
"""
from typing import Optional
from enum import Enum

from pydantic import BaseModel


class PeriodFilter(str, Enum):
    """Фильтр по периоду."""
    day = "day"
    week = "week"
    month = "month"
    all = "all"


# --- Качество сборки (#28) ---

class EmployeeQualityStats(BaseModel):
    """Статистика качества по одному сотруднику."""
    employee_id: int
    employee_name: str
    total_operations: int
    total_returns: int
    quality_percent: float


class AssemblyQualityResponse(BaseModel):
    """Ответ API качества сборки."""
    period: str
    employees: list[EmployeeQualityStats]


# --- Качество механизма (#29) ---

class MechanismQualityResponse(BaseModel):
    """Ответ API качества механизма."""
    period: str
    employees: list[EmployeeQualityStats]


# --- Качество полировки (#30) ---

class PolishingQualityStats(BaseModel):
    """Статистика качества полировки по одному полировщику."""
    employee_id: int
    employee_name: str
    total_polished: int
    total_returns: int
    quality_percent: float


class PolishingQualityResponse(BaseModel):
    """Ответ API качества полировки."""
    period: str
    polishers: list[PolishingQualityStats]


# --- Загрузка полировщиков (#31) ---

class PolisherWorkloadStats(BaseModel):
    """Статистика загрузки одного полировщика."""
    employee_id: int
    employee_name: str
    in_progress: int
    completed: int
    total_hours: float
    simple_count: int
    difficult_count: int
    with_bracelet: int
    without_bracelet: int
    avg_hours: Optional[float] = None


class PolishingWorkloadResponse(BaseModel):
    """Ответ API загрузки полировщиков."""
    polishers: list[PolisherWorkloadStats]


# --- Производительность за период (#32) ---

class EmployeePerformanceStats(BaseModel):
    """Статистика производительности одного сотрудника."""
    employee_id: int
    employee_name: str
    assembly_count: int
    mechanism_count: int
    polishing_count: int
    total_count: int


class PerformanceResponse(BaseModel):
    """Ответ API производительности."""
    period: str
    employees: list[EmployeePerformanceStats]
    total_assembly: int
    total_mechanism: int
    total_polishing: int
    total_operations: int


# --- Сводка возвратов (#32) ---

class ReasonSummary(BaseModel):
    """Сводка по одной причине возврата."""
    reason_code: str
    reason_name: str
    count: int


class EmployeeReturnStats(BaseModel):
    """Статистика возвратов по сотруднику."""
    employee_id: int
    employee_name: str
    total_returns: int


class ReturnsSummaryResponse(BaseModel):
    """Ответ API сводки возвратов."""
    period: str
    total_returns: int
    by_reason: list[ReasonSummary]
    top_employees: list[EmployeeReturnStats]
