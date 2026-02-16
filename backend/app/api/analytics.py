"""
API эндпоинты аналитики — Sprint 6.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    PeriodFilter,
    AssemblyQualityResponse,
    MechanismQualityResponse,
    PolishingQualityResponse,
    PolishingWorkloadResponse,
    PerformanceResponse,
    ReturnsSummaryResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/quality/assembly", response_model=AssemblyQualityResponse)
def get_assembly_quality(
    period: PeriodFilter = Query(PeriodFilter.all),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Качество сборки по сотрудникам."""
    svc = AnalyticsService(db)
    return svc.assembly_quality(period=period.value, employee_id=employee_id)


@router.get("/quality/mechanism", response_model=MechanismQualityResponse)
def get_mechanism_quality(
    period: PeriodFilter = Query(PeriodFilter.all),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Качество ремонта механизма по сотрудникам."""
    svc = AnalyticsService(db)
    return svc.mechanism_quality(period=period.value, employee_id=employee_id)


@router.get("/quality/polishing", response_model=PolishingQualityResponse)
def get_polishing_quality(
    period: PeriodFilter = Query(PeriodFilter.all),
    polisher_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Качество полировки по полировщикам."""
    svc = AnalyticsService(db)
    return svc.polishing_quality(period=period.value, polisher_id=polisher_id)


@router.get("/polishing/workload", response_model=PolishingWorkloadResponse)
def get_polishing_workload(
    db: Session = Depends(get_db),
):
    """Текущая загрузка полировщиков."""
    svc = AnalyticsService(db)
    return svc.polishing_workload()


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(
    period: PeriodFilter = Query(PeriodFilter.all),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Производительность за период по сотрудникам."""
    svc = AnalyticsService(db)
    return svc.performance(period=period.value, employee_id=employee_id)


@router.get("/returns/summary", response_model=ReturnsSummaryResponse)
def get_returns_summary(
    period: PeriodFilter = Query(PeriodFilter.all),
    db: Session = Depends(get_db),
):
    """Сводка возвратов за период."""
    svc = AnalyticsService(db)
    return svc.returns_summary(period=period.value)
