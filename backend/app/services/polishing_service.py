"""
Сервис для работы с полировкой.
"""
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models.polishing import PolishingDetails
from app.models.history import HistoryEvent
from app.schemas.polishing import PolishingDetailsCreate, PolishingDetailsUpdate


class PolishingService:
    """Сервис для управления полировкой."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_receipt_id(self, receipt_id: int) -> Optional[PolishingDetails]:
        """Получить детали полировки по ID квитанции."""
        return (
            self.db.query(PolishingDetails)
            .options(joinedload(PolishingDetails.polisher))
            .filter(PolishingDetails.receipt_id == receipt_id)
            .first()
        )
    
    def get_in_progress(self, skip: int = 0, limit: int = 100) -> list[PolishingDetails]:
        """Получить список часов в полировке (не возвращены)."""
        return (
            self.db.query(PolishingDetails)
            .options(joinedload(PolishingDetails.polisher))
            .filter(PolishingDetails.returned_at.is_(None))
            .order_by(desc(PolishingDetails.sent_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_polisher(
        self,
        polisher_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PolishingDetails]:
        """Получить все записи полировки по полировщику."""
        return (
            self.db.query(PolishingDetails)
            .filter(PolishingDetails.polisher_id == polisher_id)
            .order_by(desc(PolishingDetails.sent_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(
        self,
        data: PolishingDetailsCreate,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> PolishingDetails:
        """Создать запись о передаче в полировку с логированием."""
        # Проверяем, нет ли уже записи для этой квитанции
        existing = self.get_by_receipt_id(data.receipt_id)
        if existing:
            raise ValueError(f"Квитанция {data.receipt_id} уже в полировке")
        
        polishing = PolishingDetails(
            receipt_id=data.receipt_id,
            polisher_id=data.polisher_id,
            metal_type=data.metal_type,
            bracelet=data.bracelet,
            difficult=data.difficult,
            comment=data.comment,
        )
        self.db.add(polishing)
        self.db.flush()
        
        # Получаем имя полировщика для истории
        from app.models.employee import Employee
        polisher = self.db.query(Employee).get(data.polisher_id)
        
        # Логируем передачу в полировку
        history_event = HistoryEvent(
            receipt_id=data.receipt_id,
            event_type="polishing_sent",
            payload={
                "polisher_id": data.polisher_id,
                "polisher_name": polisher.name if polisher else None,
                "metal_type": data.metal_type,
                "bracelet": data.bracelet,
                "difficult": data.difficult,
                "comment": data.comment,
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)
        
        self.db.flush()
        self.db.refresh(polishing)
        return polishing
    
    def mark_returned(
        self,
        receipt_id: int,
        returned_at: Optional[datetime] = None,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> PolishingDetails:
        """Отметить возврат из полировки с логированием."""
        polishing = self.get_by_receipt_id(receipt_id)
        if not polishing:
            raise ValueError(f"Запись о полировке для квитанции {receipt_id} не найдена")
        
        if polishing.returned_at:
            raise ValueError(f"Часы уже возвращены из полировки")
        
        polishing.returned_at = returned_at or datetime.utcnow()
        
        # Логируем возврат из полировки
        history_event = HistoryEvent(
            receipt_id=receipt_id,
            event_type="polishing_returned",
            payload={
                "polisher_id": polishing.polisher_id,
                "returned_at": polishing.returned_at.isoformat(),
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)
        
        self.db.flush()
        self.db.refresh(polishing)
        return polishing
    
    def get_stats(self, polisher_id: int) -> dict:
        """Получить статистику по полировщику."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        # В работе
        in_progress = (
            self.db.query(func.count(PolishingDetails.receipt_id))
            .filter(
                PolishingDetails.polisher_id == polisher_id,
                PolishingDetails.returned_at.is_(None),
            )
            .scalar()
        )
        
        # За сегодня
        completed_today = (
            self.db.query(func.count(PolishingDetails.receipt_id))
            .filter(
                PolishingDetails.polisher_id == polisher_id,
                PolishingDetails.returned_at >= today_start,
            )
            .scalar()
        )
        
        # За неделю
        completed_week = (
            self.db.query(func.count(PolishingDetails.receipt_id))
            .filter(
                PolishingDetails.polisher_id == polisher_id,
                PolishingDetails.returned_at >= week_start,
            )
            .scalar()
        )
        
        # За месяц
        completed_month = (
            self.db.query(func.count(PolishingDetails.receipt_id))
            .filter(
                PolishingDetails.polisher_id == polisher_id,
                PolishingDetails.returned_at >= month_start,
            )
            .scalar()
        )
        
        from app.models.employee import Employee
        polisher = self.db.query(Employee).get(polisher_id)
        
        return {
            "polisher_id": polisher_id,
            "polisher_name": polisher.name if polisher else "Unknown",
            "in_progress": in_progress,
            "completed_today": completed_today,
            "completed_week": completed_week,
            "completed_month": completed_month,
        }
