"""
Сервис для работы с операциями.
"""
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models.operation import Operation, OperationType
from app.models.employee import Employee
from app.models.receipt import Receipt
from app.models.history import HistoryEvent
from app.schemas.operation import OperationCreate
from app.core.exceptions import NotFoundException


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
    
    def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Operation], int]:
        """Получить список всех операций с пагинацией и общим количеством."""
        total = self.db.query(func.count(Operation.id)).scalar()
        items = (
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
        return items, total

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
        receipt = self.db.query(Receipt).get(data.receipt_id)
        if not receipt:
            raise NotFoundException("Квитанция", data.receipt_id)

        operation_type = self.db.query(OperationType).get(data.operation_type_id)
        if not operation_type:
            raise NotFoundException("Тип операции", data.operation_type_id)

        employee = self.db.query(Employee).get(data.employee_id)
        if not employee:
            raise NotFoundException("Сотрудник", data.employee_id)

        operation = Operation(
            receipt_id=data.receipt_id,
            operation_type_id=data.operation_type_id,
            employee_id=data.employee_id,
        )
        self.db.add(operation)
        self.db.flush()  # Получаем ID до коммита
        
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
