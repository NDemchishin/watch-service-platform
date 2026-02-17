"""
API endpoints для управления сотрудниками.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
)
from app.services.employee_service import EmployeeService

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    inactive_only: bool = Query(False),
    role: Optional[str] = Query(None, description="Фильтр по роли: master или polisher"),
    db: Session = Depends(get_db),
):
    """Получить список сотрудников."""
    service = EmployeeService(db)

    if inactive_only:
        employees = service.get_inactive(skip=skip, limit=limit, role=role)
    elif active_only:
        employees = service.get_active(skip=skip, limit=limit, role=role)
    else:
        employees = service.get_all(skip=skip, limit=limit, role=role)

    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(e) for e in employees],
        total=len(employees),
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Получить сотрудника по ID."""
    service = EmployeeService(db)
    employee = service.get_by_id(employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сотрудник с ID {employee_id} не найден",
        )
    
    return EmployeeResponse.model_validate(employee)


@router.get("/telegram/{telegram_id}", response_model=EmployeeResponse)
def get_employee_by_telegram(telegram_id: int, db: Session = Depends(get_db)):
    """Получить сотрудника по Telegram ID."""
    service = EmployeeService(db)
    employee = service.get_by_telegram_id(telegram_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сотрудник с Telegram ID {telegram_id} не найден",
        )
    
    return EmployeeResponse.model_validate(employee)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    """Создать нового сотрудника."""
    service = EmployeeService(db)
    employee = service.create(data)
    return EmployeeResponse.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    """Обновить данные сотрудника."""
    service = EmployeeService(db)
    employee = service.get_by_id(employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сотрудник с ID {employee_id} не найден",
        )
    
    updated = service.update(employee, data)
    return EmployeeResponse.model_validate(updated)


@router.post("/{employee_id}/deactivate", response_model=EmployeeResponse)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    """Деактивировать сотрудника (вместо удаления)."""
    service = EmployeeService(db)
    employee = service.get_by_id(employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сотрудник с ID {employee_id} не найден",
        )
    
    deactivated = service.deactivate(employee)
    return EmployeeResponse.model_validate(deactivated)


@router.post("/{employee_id}/activate", response_model=EmployeeResponse)
def activate_employee(employee_id: int, db: Session = Depends(get_db)):
    """Активировать сотрудника."""
    service = EmployeeService(db)
    employee = service.get_by_id(employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сотрудник с ID {employee_id} не найден",
        )
    
    activated = service.activate(employee)
    return EmployeeResponse.model_validate(activated)
