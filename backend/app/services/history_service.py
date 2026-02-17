"""
Сервис для работы с историей событий.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from app.models.history import HistoryEvent
from app.schemas.history import HistoryEventCreate

logger = logging.getLogger(__name__)


class HistoryService:
    """Сервис для управления историей событий."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, event_id: int) -> Optional[HistoryEvent]:
        """Получить событие по ID."""
        return self.db.query(HistoryEvent).filter(HistoryEvent.id == event_id).first()
    
    def get_by_receipt(
        self,
        receipt_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[HistoryEvent]:
        """Получить историю событий по квитанции."""
        return (
            self.db.query(HistoryEvent)
            .filter(HistoryEvent.receipt_id == receipt_id)
            .order_by(asc(HistoryEvent.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_receipt(self, receipt_id: int) -> int:
        """Получить общее количество событий по квитанции."""
        return (
            self.db.query(func.count(HistoryEvent.id))
            .filter(HistoryEvent.receipt_id == receipt_id)
            .scalar()
        )

    def count_all(self, event_type: str | None = None) -> int:
        """Получить общее количество событий с опциональной фильтрацией."""
        query = self.db.query(func.count(HistoryEvent.id))
        if event_type:
            query = query.filter(HistoryEvent.event_type == event_type)
        return query.scalar()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> list[HistoryEvent]:
        """Получить все события истории с возможной фильтрацией по типу."""
        query = self.db.query(HistoryEvent)
        
        if event_type:
            query = query.filter(HistoryEvent.event_type == event_type)
        
        return (
            query.order_by(desc(HistoryEvent.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, data: HistoryEventCreate) -> HistoryEvent:
        """Создать новое событие истории."""
        logger.info("Creating history event: receipt_id=%s, type=%s", data.receipt_id, data.event_type)
        event = HistoryEvent(
            receipt_id=data.receipt_id,
            event_type=data.event_type,
            payload=data.payload,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )
        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)
        return event
