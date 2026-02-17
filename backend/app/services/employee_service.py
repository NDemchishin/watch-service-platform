"""
Сервис для работы с сотрудниками.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.exceptions import DuplicateError
from app.core.utils import sanitize_text

logger = logging.getLogger(__name__)


class EmployeeService:
    """Сервис для управления сотрудниками."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, employee_id: int) -> Optional[Employee]:
        """Получить сотрудника по ID."""
        return self.db.query(Employee).filter(Employee.id == employee_id).first()
    
    def get_by_telegram_id(self, telegram_id: int) -> Optional[Employee]:
        """Получить сотрудника по Telegram ID."""
        return self.db.query(Employee).filter(Employee.telegram_id == telegram_id).first()
    
    def get_active(self, skip: int = 0, limit: int = 100) -> list[Employee]:
        """Получить список активных сотрудников."""
        return (
            self.db.query(Employee)
            .filter(Employee.is_active == True)
            .order_by(desc(Employee.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[Employee]:
        """Получить список всех сотрудников."""
        return (
            self.db.query(Employee)
            .order_by(desc(Employee.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_inactive(self, skip: int = 0, limit: int = 100) -> list[Employee]:
        """Получить список неактивных сотрудников."""
        return (
            self.db.query(Employee)
            .filter(Employee.is_active == False)
            .order_by(desc(Employee.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, data: EmployeeCreate) -> Employee:
        """Создать нового сотрудника."""
        logger.info("Creating employee: name=%s, telegram_id=%s", data.name, data.telegram_id)
        employee = Employee(
            name=sanitize_text(data.name, max_length=200),
            telegram_id=data.telegram_id,
            telegram_username=sanitize_text(data.telegram_username, max_length=100),
            is_active=data.is_active,
        )
        self.db.add(employee)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            logger.warning("Duplicate telegram_id: %s", data.telegram_id)
            raise DuplicateError(f"Сотрудник с telegram_id {data.telegram_id} уже существует")
        self.db.refresh(employee)
        logger.info("Employee created: id=%s, name=%s", employee.id, employee.name)
        return employee
    
    def update(self, employee: Employee, data: EmployeeUpdate) -> Employee:
        """Обновить данные сотрудника."""
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field in ("name", "telegram_username") and isinstance(value, str):
                value = sanitize_text(value, max_length=200 if field == "name" else 100)
            setattr(employee, field, value)
        
        self.db.flush()
        self.db.refresh(employee)
        return employee
    
    def deactivate(self, employee: Employee) -> Employee:
        """Деактивировать сотрудника (вместо удаления)."""
        logger.info("Deactivating employee: id=%s", employee.id)
        employee.is_active = False
        self.db.flush()
        self.db.refresh(employee)
        return employee

    def activate(self, employee: Employee) -> Employee:
        """Активировать сотрудника."""
        logger.info("Activating employee: id=%s", employee.id)
        employee.is_active = True
        self.db.flush()
        self.db.refresh(employee)
        return employee
