"""
API endpoints для управления операциями.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.operation import (
    OperationCreate,
    OperationResponse,
    OperationListResponse,
    OperationTypeResponse,
    OperationTypeListResponse,
)
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/types", response_model=OperationTypeListResponse)
def list_operation_types(db: Session = Depends(get_db)):
    """Получить список типов операций."""
    service = OperationService(db)
    types = service.get_all_types()
    
    return OperationTypeListResponse(
        items=[OperationTypeResponse.model_validate(t) for t in types],
        total=len(types),
    )


@router.get("/types/{type_code}", response_model=OperationTypeResponse)
def get_operation_type(type_code: str, db: Session = Depends(get_db)):
    """Получить тип операции по коду."""
    service = OperationService(db)
    op_type = service.get_type_by_code(type_code)
    
    if not op_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Тип операции с кодом {type_code} не найден",
        )
    
    return OperationTypeResponse.model_validate(op_type)


@router.get("", response_model=OperationListResponse)
def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список всех операций."""
    # TODO: добавить фильтрацию по квитанции
    service = OperationService(db)
    # Пока возвращаем пустой список, так как нет метода get_all
    return OperationListResponse(items=[], total=0)


@router.get("/{operation_id}", response_model=OperationResponse)
def get_operation(operation_id: int, db: Session = Depends(get_db)):
    """Получить операцию по ID."""
    service = OperationService(db)
    operation = service.get_by_id(operation_id)
    
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Операция с ID {operation_id} не найдена",
        )
    
    return OperationResponse.model_validate(operation)


@router.get("/receipt/{receipt_id}", response_model=OperationListResponse)
def get_operations_by_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Получить все операции по квитанции."""
    service = OperationService(db)
    operations = service.get_by_receipt(receipt_id)
    
    return OperationListResponse(
        items=[OperationResponse.model_validate(op) for op in operations],
        total=len(operations),
    )


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
def create_operation(
    data: OperationCreate,
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Создать новую операцию."""
    service = OperationService(db)
    operation = service.create(
        data=data,
        telegram_id=telegram_id,
        telegram_username=telegram_username,
    )
    return OperationResponse.model_validate(operation)
