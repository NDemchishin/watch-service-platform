"""
Сервис для работы с возвратами.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models.return_ import Return, ReturnReason, ReturnReasonLink
from app.models.employee import Employee
from app.models.receipt import Receipt
from app.models.history import HistoryEvent
from app.schemas.return_ import ReturnCreate, ReturnReasonLinkCreate
from app.core.exceptions import NotFoundException
from app.core.utils import sanitize_text

logger = logging.getLogger(__name__)


class ReturnService:
    """Сервис для управления возвратами."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, return_id: int) -> Optional[Return]:
        """Получить возврат по ID с подгрузкой связанных данных."""
        return (
            self.db.query(Return)
            .options(
                joinedload(Return.reasons).joinedload(ReturnReasonLink.reason),
                joinedload(Return.reasons).joinedload(ReturnReasonLink.guilty_employee),
            )
            .filter(Return.id == return_id)
            .first()
        )
    
    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Return], int]:
        """Получить список всех возвратов с пагинацией и общим количеством."""
        total = self.db.query(func.count(Return.id)).scalar()
        items = (
            self.db.query(Return)
            .options(
                joinedload(Return.reasons).joinedload(ReturnReasonLink.reason),
                joinedload(Return.reasons).joinedload(ReturnReasonLink.guilty_employee),
            )
            .order_by(desc(Return.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def get_by_receipt(self, receipt_id: int) -> list[Return]:
        """Получить все возвраты по квитанции."""
        return (
            self.db.query(Return)
            .options(
                joinedload(Return.reasons).joinedload(ReturnReasonLink.reason),
                joinedload(Return.reasons).joinedload(ReturnReasonLink.guilty_employee),
            )
            .filter(Return.receipt_id == receipt_id)
            .order_by(desc(Return.created_at))
            .all()
        )
    
    def get_all_reasons(self) -> list[ReturnReason]:
        """Получить все причины возврата."""
        return self.db.query(ReturnReason).all()
    
    def get_reason_by_code(self, code: str) -> Optional[ReturnReason]:
        """Получить причину возврата по коду."""
        return self.db.query(ReturnReason).filter(ReturnReason.code == code).first()
    
    def create(
        self,
        data: ReturnCreate,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Return:
        """Создать новый возврат с логированием в историю."""
        logger.info("Creating return: receipt_id=%s", data.receipt_id)
        receipt = self.db.query(Receipt).get(data.receipt_id)
        if not receipt:
            raise NotFoundException("Квитанция", data.receipt_id)

        # Валидация FK для каждой причины
        for reason_link in data.reasons:
            reason = self.db.query(ReturnReason).get(reason_link.reason_id)
            if not reason:
                raise NotFoundException("Причина возврата", reason_link.reason_id)
            if reason_link.guilty_employee_id:
                guilty = self.db.query(Employee).get(reason_link.guilty_employee_id)
                if not guilty:
                    raise NotFoundException("Сотрудник", reason_link.guilty_employee_id)

        # Создаем возврат
        return_record = Return(
            receipt_id=data.receipt_id,
            comment=sanitize_text(data.comment),
        )
        self.db.add(return_record)
        self.db.flush()  # Получаем ID возврата
        
        # Добавляем причины возврата
        reasons_data = []
        for reason_link in data.reasons:
            return_reason_link = ReturnReasonLink(
                return_id=return_record.id,
                reason_id=reason_link.reason_id,
                guilty_employee_id=reason_link.guilty_employee_id,
            )
            self.db.add(return_reason_link)
            
            # Собираем данные для истории
            reason = self.db.query(ReturnReason).get(reason_link.reason_id)
            guilty_name = None
            if reason_link.guilty_employee_id:
                guilty = self.db.query(Employee).get(reason_link.guilty_employee_id)
                guilty_name = guilty.name if guilty else None
            
            reasons_data.append({
                "reason_id": reason_link.reason_id,
                "reason_code": reason.code if reason else None,
                "reason_name": reason.name if reason else None,
                "affects": reason.affects if reason else None,
                "guilty_employee_id": reason_link.guilty_employee_id,
                "guilty_employee_name": guilty_name,
            })
        
        # Логируем возврат в историю
        history_event = HistoryEvent(
            receipt_id=data.receipt_id,
            event_type="return_created",
            payload={
                "return_id": return_record.id,
                "comment": data.comment,
                "reasons": reasons_data,
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)
        
        self.db.flush()
        self.db.refresh(return_record)
        logger.info("Return created: id=%s, receipt_id=%s", return_record.id, data.receipt_id)
        return return_record
