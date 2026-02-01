"""
Сервис для работы с историей событий.
"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.history import HistoryEvent
from app.schemas.history import HistoryEventCreate


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
            .order_by(desc(HistoryEvent.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
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
        event = HistoryEvent(
            receipt_id=data.receipt_id,
            event_type=data.event_type,
            payload=data.payload,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
