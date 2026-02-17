"""
API endpoints для работы с историей событий.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.history import (
    HistoryEventCreate,
    HistoryEventResponse,
    HistoryEventListResponse,
)
from app.services.history_service import HistoryService

router = APIRouter(
    prefix="/history",
    tags=["history"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=HistoryEventListResponse)
def list_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Получить список событий истории."""
    service = HistoryService(db)
    events = service.get_all(skip=skip, limit=limit, event_type=event_type)
    total = service.count_all(event_type=event_type)

    return HistoryEventListResponse(
        items=[HistoryEventResponse.model_validate(e) for e in events],
        total=total,
    )


@router.get("/{event_id}", response_model=HistoryEventResponse)
def get_history_event(event_id: int, db: Session = Depends(get_db)):
    """Получить событие истории по ID."""
    service = HistoryService(db)
    event = service.get_by_id(event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Событие истории с ID {event_id} не найдено",
        )
    
    return HistoryEventResponse.model_validate(event)


@router.get("/receipt/{receipt_id}", response_model=HistoryEventListResponse)
def get_history_by_receipt(
    receipt_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить историю событий по квитанции."""
    service = HistoryService(db)
    events = service.get_by_receipt(receipt_id, skip=skip, limit=limit)
    total = service.count_by_receipt(receipt_id)

    return HistoryEventListResponse(
        items=[HistoryEventResponse.model_validate(e) for e in events],
        total=total,
    )


@router.post("", response_model=HistoryEventResponse, status_code=status.HTTP_201_CREATED)
def add_history_event(
    data: HistoryEventCreate,
    db: Session = Depends(get_db),
):
    """Добавить событие в историю."""
    service = HistoryService(db)
    event = service.create(data)
    return HistoryEventResponse.model_validate(event)
