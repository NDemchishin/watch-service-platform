"""
API endpoints для управления квитанциями.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptUpdate,
    ReceiptResponse,
    ReceiptListResponse,
    ReceiptWithHistoryResponse,
)
from app.schemas.history import HistoryEventResponse
from app.services.receipt_service import ReceiptService
from app.services.history_service import HistoryService

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("", response_model=ReceiptListResponse)
def list_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список квитанций."""
    service = ReceiptService(db)
    receipts = service.get_all(skip=skip, limit=limit)
    
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
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
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
        telegram_id=telegram_id,
        telegram_username=telegram_username,
    )
    
    return ReceiptResponse.model_validate(updated)
