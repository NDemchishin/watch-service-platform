"""
API endpoints для управления возвратами.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.return_ import (
    ReturnCreate,
    ReturnResponse,
    ReturnListResponse,
    ReturnReasonResponse,
    ReturnReasonListResponse,
)
from app.services.return_service import ReturnService

router = APIRouter(
    prefix="/returns",
    tags=["returns"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/reasons", response_model=ReturnReasonListResponse)
def list_return_reasons(db: Session = Depends(get_db)):
    """Получить список причин возврата."""
    service = ReturnService(db)
    reasons = service.get_all_reasons()

    return ReturnReasonListResponse(
        items=[ReturnReasonResponse.model_validate(r) for r in reasons],
        total=len(reasons),
    )


@router.get("/reasons/{reason_code}", response_model=ReturnReasonResponse)
def get_return_reason(reason_code: str, db: Session = Depends(get_db)):
    """Получить причину возврата по коду."""
    service = ReturnService(db)
    reason = service.get_reason_by_code(reason_code)

    if not reason:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Причина возврата с кодом {reason_code} не найдена",
        )

    return ReturnReasonResponse.model_validate(reason)


@router.get("", response_model=ReturnListResponse)
def list_returns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список всех возвратов."""
    service = ReturnService(db)
    items, total = service.get_all(skip=skip, limit=limit)

    return ReturnListResponse(
        items=[ReturnResponse.model_validate(r) for r in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/receipt/{receipt_id}", response_model=ReturnListResponse)
def get_returns_by_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Получить все возвраты по квитанции."""
    service = ReturnService(db)
    returns = service.get_by_receipt(receipt_id)

    return ReturnListResponse(
        items=[ReturnResponse.model_validate(r) for r in returns],
        total=len(returns),
    )


@router.get("/{return_id}", response_model=ReturnResponse)
def get_return(return_id: int, db: Session = Depends(get_db)):
    """Получить возврат по ID."""
    service = ReturnService(db)
    return_record = service.get_by_id(return_id)

    if not return_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Возврат с ID {return_id} не найден",
        )

    return ReturnResponse.model_validate(return_record)


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
def create_return(
    data: ReturnCreate,
    telegram_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Создать новый возврат."""
    service = ReturnService(db)
    return_record = service.create(
        data=data,
        telegram_id=telegram_id,
        telegram_username=telegram_username,
    )
    return ReturnResponse.model_validate(return_record)
