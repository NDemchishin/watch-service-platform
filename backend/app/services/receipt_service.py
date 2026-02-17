"""
Сервис для работы с квитанциями.
"""
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, exists, and_, func

from app.models.receipt import Receipt
from app.models.history import HistoryEvent
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.services.notification_service import NotificationService
from app.core.exceptions import DuplicateError
from app.core.utils import sanitize_text

logger = logging.getLogger(__name__)


class ReceiptService:
    """Сервис для управления квитанциями."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, receipt_id: int) -> Optional[Receipt]:
        """Получить квитанцию по ID."""
        return self.db.query(Receipt).filter(Receipt.id == receipt_id).first()
    
    def get_by_number(self, receipt_number: str) -> Optional[Receipt]:
        """Получить квитанцию по номеру."""
        return self.db.query(Receipt).filter(Receipt.receipt_number == receipt_number).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Receipt], int]:
        """Получить список всех квитанций с общим количеством."""
        total = self.db.query(func.count(Receipt.id)).scalar()
        items = (
            self.db.query(Receipt)
            .order_by(desc(Receipt.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total
    
    def get_urgent(self) -> list[Receipt]:
        """
        Получить список срочных часов.
        Согласно ТЗ Sprint 3: только часы с current_deadline, не прошедшие ОТК.
        Один SQL-запрос с NOT EXISTS вместо N+1.
        """
        otk_exists = (
            exists()
            .where(
                and_(
                    HistoryEvent.receipt_id == Receipt.id,
                    HistoryEvent.event_type == "passed_otk",
                )
            )
        )

        return (
            self.db.query(Receipt)
            .filter(
                Receipt.current_deadline.isnot(None),
                ~otk_exists,
            )
            .order_by(Receipt.current_deadline)
            .all()
        )
    
    def create(
        self,
        data: ReceiptCreate,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Receipt:
        """Создать новую квитанцию с логированием в историю."""
        logger.info("Creating receipt: number=%s", data.receipt_number)
        receipt = Receipt(
            receipt_number=sanitize_text(data.receipt_number, max_length=100),
            current_deadline=data.current_deadline,
        )
        self.db.add(receipt)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            logger.warning("Duplicate receipt number: %s", data.receipt_number)
            raise DuplicateError(f"Квитанция с номером {data.receipt_number} уже существует")
        
        # Логируем создание в историю
        history_event = HistoryEvent(
            receipt_id=receipt.id,
            event_type="receipt_created",
            payload={
                "receipt_number": data.receipt_number,
                "deadline": data.current_deadline.isoformat() if data.current_deadline else None,
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)

        self.db.flush()
        self.db.refresh(receipt)

        # Планируем уведомления если есть дедлайн
        if data.current_deadline:
            notification_service = NotificationService(self.db)
            notification_service.schedule_notifications(receipt.id, data.current_deadline)

        logger.info("Receipt created: id=%s, number=%s", receipt.id, receipt.receipt_number)
        return receipt

    def update_deadline(
        self,
        receipt: Receipt,
        new_deadline: Optional[datetime],
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Receipt:
        """Обновить дедлайн квитанции с логированием в историю."""
        logger.info("Updating deadline: receipt_id=%s", receipt.id)
        old_deadline = receipt.current_deadline
        receipt.current_deadline = new_deadline
        
        # Логируем изменение дедлайна
        history_event = HistoryEvent(
            receipt_id=receipt.id,
            event_type="deadline_changed",
            payload={
                "old_deadline": old_deadline.isoformat() if old_deadline else None,
                "new_deadline": new_deadline.isoformat() if new_deadline else None,
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)

        self.db.flush()
        self.db.refresh(receipt)

        # Перепланируем уведомления
        notification_service = NotificationService(self.db)
        if new_deadline:
            notification_service.schedule_notifications(receipt.id, new_deadline)
        else:
            notification_service.cancel_notifications(receipt.id)

        return receipt
