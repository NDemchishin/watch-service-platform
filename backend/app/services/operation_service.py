"""
Сервис для работы с операциями.
"""
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.operation import Operation, OperationType
from app.models.history import HistoryEvent
from app.schemas.operation import OperationCreate


class OperationService:
    """Сервис для управления операциями."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, operation_id: int) -> Optional[Operation]:
        """Получить операцию по ID с подгрузкой связанных данных."""
        return (
            self.db.query(Operation)
            .options(
                joinedload(Operation.operation_type),
                joinedload(Operation.employee),
            )
            .filter(Operation.id == operation_id)
            .first()
        )
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[Operation]:
        """Получить список всех операций с пагинацией."""
        return (
            self.db.query(Operation)
            .options(
                joinedload(Operation.operation_type),
                joinedload(Operation.employee),
            )
            .order_by(desc(Operation.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_receipt(self, receipt_id: int) -> list[Operation]:
        """Получить все операции по квитанции."""
        return (
            self.db.query(Operation)
            .options(
                joinedload(Operation.operation_type),
                joinedload(Operation.employee),
            )
            .filter(Operation.receipt_id == receipt_id)
            .order_by(desc(Operation.created_at))
            .all()
        )
    
    def get_all_types(self) -> list[OperationType]:
        """Получить все типы операций."""
        return self.db.query(OperationType).all()
    
    def get_type_by_code(self, code: str) -> Optional[OperationType]:
        """Получить тип операции по коду."""
        return self.db.query(OperationType).filter(OperationType.code == code).first()
    
    def create(
        self,
        data: OperationCreate,
        telegram_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
    ) -> Operation:
        """Создать новую операцию с логированием в историю."""
        operation = Operation(
            receipt_id=data.receipt_id,
            operation_type_id=data.operation_type_id,
            employee_id=data.employee_id,
        )
        self.db.add(operation)
        self.db.flush()  # Получаем ID до коммита
        
        # Получаем данные для истории
        operation_type = self.db.query(OperationType).get(data.operation_type_id)
        from app.models.employee import Employee
        employee = self.db.query(Employee).get(data.employee_id)
        
        # Логируем создание операции
        history_event = HistoryEvent(
            receipt_id=data.receipt_id,
            event_type="operation_created",
            payload={
                "operation_id": operation.id,
                "operation_type": operation_type.code if operation_type else None,
                "operation_type_name": operation_type.name if operation_type else None,
                "employee_id": data.employee_id,
                "employee_name": employee.name if employee else None,
            },
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )
        self.db.add(history_event)
        
        self.db.flush()
        self.db.refresh(operation)
        return operation
