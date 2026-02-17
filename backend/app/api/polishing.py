"""
API endpoints для управления полировкой.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.polishing import (
    PolishingDetailsCreate,
    PolishingDetailsUpdate,
    PolishingDetailsResponse,
    PolishingDetailsListResponse,
    PolishingStatsResponse,
)
from app.services.polishing_service import PolishingService

router = APIRouter(
    prefix="/polishing",
    tags=["polishing"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/in-progress", response_model=PolishingDetailsListResponse)
def list_in_progress(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список часов в полировке (не возвращены)."""
    service = PolishingService(db)
    items, total = service.get_in_progress(skip=skip, limit=limit)

    return PolishingDetailsListResponse(
        items=[PolishingDetailsResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/receipt/{receipt_id}", response_model=PolishingDetailsResponse)
def get_polishing_by_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Получить детали полировки по ID квитанции."""
    service = PolishingService(db)
    polishing = service.get_by_receipt_id(receipt_id)
    
    if not polishing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись о полировке для квитанции {receipt_id} не найдена",
        )
    
    return PolishingDetailsResponse.model_validate(polishing)


@router.get("/polisher/{polisher_id}", response_model=PolishingDetailsListResponse)
def get_polishing_by_polisher(
    polisher_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить все записи полировки по полировщику."""
    service = PolishingService(db)
    items, total = service.get_by_polisher(polisher_id, skip=skip, limit=limit)

    return PolishingDetailsListResponse(
        items=[PolishingDetailsResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats/{polisher_id}", response_model=PolishingStatsResponse)
def get_polisher_stats(polisher_id: int, db: Session = Depends(get_db)):
    """Получить статистику по полировщику."""
    service = PolishingService(db)
    stats = service.get_stats(polisher_id)
    
    return PolishingStatsResponse(**stats)


@router.post("", response_model=PolishingDetailsResponse, status_code=status.HTTP_201_CREATED)
def create_polishing(
    data: PolishingDetailsCreate,
    db: Session = Depends(get_db),
):
    """Создать запись о передаче в полировку."""
    service = PolishingService(db)

    try:
        polishing = service.create(
            data=data,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return PolishingDetailsResponse.model_validate(polishing)


@router.post("/receipt/{receipt_id}/return", response_model=PolishingDetailsResponse)
def mark_polishing_returned(
    receipt_id: int,
    data: PolishingDetailsUpdate,
    db: Session = Depends(get_db),
):
    """Отметить возврат из полировки."""
    service = PolishingService(db)

    try:
        polishing = service.mark_returned(
            receipt_id=receipt_id,
            returned_at=data.returned_at,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return PolishingDetailsResponse.model_validate(polishing)
