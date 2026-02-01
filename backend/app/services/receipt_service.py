"""
Сервис для работы с квитанциями.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.receipt import Receipt
from app.models.history import HistoryEvent
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate


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
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[Receipt]:
        """Получить список всех квитанций."""
        return (
            self.db.query(Receipt)
            .order_by(desc(Receipt.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(
        self,
        data: ReceiptCreate,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Receipt:
        """Создать новую квитанцию с логированием в историю."""
        # Проверка на уникальность номера квитанции
        existing = self.get_by_number(data.receipt_number)
        if existing:
            raise ValueError(f"Квитанция с номером {data.receipt_number} уже существует")
        
        receipt = Receipt(
            receipt_number=data.receipt_number,
            current_deadline=data.current_deadline,
        )
        self.db.add(receipt)
        self.db.flush()  # Получаем ID до коммита
        
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
        
        self.db.commit()
        self.db.refresh(receipt)
        return receipt
    
    def update_deadline(
        self,
        receipt: Receipt,
        new_deadline: Optional[datetime],
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Receipt:
        """Обновить дедлайн квитанции с логированием в историю."""
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
        
        self.db.commit()
        self.db.refresh(receipt)
        return receipt
