"""
Сервис для работы с возвратами.
"""
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.return_ import Return, ReturnReason, ReturnReasonLink
from app.models.history import HistoryEvent
from app.schemas.return_ import ReturnCreate, ReturnReasonLinkCreate


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
        # Создаем возврат
        return_record = Return(
            receipt_id=data.receipt_id,
            comment=data.comment,
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
                from app.models.employee import Employee
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
        
        self.db.commit()
        self.db.refresh(return_record)
        return return_record
