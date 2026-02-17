"""
API endpoints для управления квитанциями.
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptUpdate,
    ReceiptResponse,
    ReceiptListResponse,
    ReceiptWithHistoryResponse,
    ReceiptGetOrCreate,
    AssignMasterRequest,
)
from app.schemas.history import HistoryEventResponse, HistoryEventCreate
from app.services.receipt_service import ReceiptService
from app.services.history_service import HistoryService
from app.services.employee_service import EmployeeService

router = APIRouter(
    prefix="/receipts",
    tags=["receipts"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=ReceiptListResponse)
def list_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список квитанций."""
    service = ReceiptService(db)
    items, total = service.get_all(skip=skip, limit=limit)

    return ReceiptListResponse(
        items=[ReceiptResponse.model_validate(r) for r in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/urgent", response_model=ReceiptListResponse)
def get_urgent_receipts(
    db: Session = Depends(get_db),
):
    """Получить список срочных часов (с дедлайном, не прошедших ОТК)."""
    service = ReceiptService(db)
    receipts = service.get_urgent()
    
    return ReceiptListResponse(
        items=[ReceiptResponse.model_validate(r) for r in receipts],
        total=len(receipts),
    )


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Получить квитанцию по ID."""
    service = ReceiptService(db)
    receipt = service.get_by_id(receipt_id)
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {receipt_id} не найдена",
        )
    
    return ReceiptResponse.model_validate(receipt)


@router.get("/number/{receipt_number}", response_model=ReceiptResponse)
def get_receipt_by_number(receipt_number: str, db: Session = Depends(get_db)):
    """Получить квитанцию по номеру."""
    service = ReceiptService(db)
    receipt = service.get_by_number(receipt_number)
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с номером {receipt_number} не найдена",
        )
    
    return ReceiptResponse.model_validate(receipt)


@router.post("/get-or-create", response_model=ReceiptResponse)
def get_or_create_receipt(
    data: ReceiptGetOrCreate,
    db: Session = Depends(get_db),
):
    """
    Получить квитанцию по номеру или создать новую.
    Согласно ТЗ Sprint 3: квитанция создаётся автоматически, если её нет.
    """
    service = ReceiptService(db)
    
    # Пробуем найти существующую
    existing = service.get_by_number(data.receipt_number)
    if existing:
        return ReceiptResponse.model_validate(existing)
    
    # Создаём новую
    try:
        receipt = service.create(
            data=ReceiptCreate(receipt_number=data.receipt_number),
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return ReceiptResponse.model_validate(receipt)


@router.get("/{receipt_id}/history", response_model=ReceiptWithHistoryResponse)
def get_receipt_with_history(receipt_id: int, db: Session = Depends(get_db)):
    """Получить квитанцию с полной историей."""
    receipt_service = ReceiptService(db)
    history_service = HistoryService(db)
    
    receipt = receipt_service.get_by_id(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {receipt_id} не найдена",
        )
    
    history = history_service.get_by_receipt(receipt_id)
    
    response_data = ReceiptResponse.model_validate(receipt).model_dump()
    response_data["history"] = [HistoryEventResponse.model_validate(h) for h in history]
    
    return ReceiptWithHistoryResponse(**response_data)


@router.post("", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_receipt(
    data: ReceiptCreate,
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Создать новую квитанцию."""
    service = ReceiptService(db)
    
    try:
        receipt = service.create(
            data=data,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return ReceiptResponse.model_validate(receipt)


@router.patch("/{receipt_id}/deadline", response_model=ReceiptResponse)
def update_deadline(
    receipt_id: int,
    data: ReceiptUpdate,
    db: Session = Depends(get_db),
):
    """Обновить дедлайн квитанции."""
    service = ReceiptService(db)
    receipt = service.get_by_id(receipt_id)

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {receipt_id} не найдена",
        )

    updated = service.update_deadline(
        receipt=receipt,
        new_deadline=data.current_deadline,
        telegram_id=data.telegram_id,
        telegram_username=data.telegram_username,
    )

    return ReceiptResponse.model_validate(updated)


@router.post("/assign-master", response_model=ReceiptResponse)
def assign_to_master(
    data: AssignMasterRequest,
    db: Session = Depends(get_db),
):
    """
    Выдать часы мастеру.
    Согласно ТЗ Sprint 3: создаёт history_event: sent_to_master
    """
    receipt_service = ReceiptService(db)
    history_service = HistoryService(db)
    employee_service = EmployeeService(db)

    receipt = receipt_service.get_by_id(data.receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {data.receipt_id} не найдена",
        )

    master = employee_service.get_by_id(data.master_id)
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Мастер с ID {data.master_id} не найден",
        )

    # Если срочные, обновляем дедлайн
    if data.is_urgent and data.deadline:
        receipt_service.update_deadline(
            receipt=receipt,
            new_deadline=data.deadline,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )

    # Создаём событие истории
    history_data = HistoryEventCreate(
        receipt_id=data.receipt_id,
        event_type="sent_to_master",
        payload={
            "master_id": data.master_id,
            "master_name": master.name,
            "urgent": data.is_urgent,
            "deadline": data.deadline.isoformat() if data.deadline else None,
        },
        telegram_id=data.telegram_id,
        telegram_username=data.telegram_username,
    )
    history_service.create(history_data)

    return ReceiptResponse.model_validate(receipt)


@router.post("/{receipt_id}/otk-pass", response_model=ReceiptResponse)
def otk_pass(
    receipt_id: int,
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Отметить прохождение ОТК.
    Согласно ТЗ Sprint 3: создаёт history_event: passed_otk
    """
    receipt_service = ReceiptService(db)
    history_service = HistoryService(db)
    
    receipt = receipt_service.get_by_id(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {receipt_id} не найдена",
        )
    
    # Создаём событие истории
    history_data = HistoryEventCreate(
        receipt_id=receipt_id,
        event_type="passed_otk",
        payload={},
        telegram_id=telegram_id,
        telegram_username=telegram_username,
    )
    history_service.create(history_data)
    
    return ReceiptResponse.model_validate(receipt)


@router.post("/{receipt_id}/initiate-return", response_model=ReceiptResponse)
def initiate_return(
    receipt_id: int,
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Инициировать возврат.
    Согласно ТЗ Sprint 3: создаёт history_event: return_initiated (заглушка).
    Полная логика возвратов - Sprint 4.
    """
    receipt_service = ReceiptService(db)
    history_service = HistoryService(db)
    
    receipt = receipt_service.get_by_id(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Квитанция с ID {receipt_id} не найдена",
        )
    
    # Создаём событие истории (заглушка)
    history_data = HistoryEventCreate(
        receipt_id=receipt_id,
        event_type="return_initiated",
        payload={
            "note": "Sprint 3 - заглушка. Полная логика возвратов в Sprint 4."
        },
        telegram_id=telegram_id,
        telegram_username=telegram_username,
    )
    history_service.create(history_data)
    
    return ReceiptResponse.model_validate(receipt)
