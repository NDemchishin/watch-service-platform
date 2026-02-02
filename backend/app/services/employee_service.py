"""
Сервис для работы с сотрудниками.
"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


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
        employee = Employee(
            name=data.name,
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
            is_active=data.is_active,
        )
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def update(self, employee: Employee, data: EmployeeUpdate) -> Employee:
        """Обновить данные сотрудника."""
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def deactivate(self, employee: Employee) -> Employee:
        """Деактивировать сотрудника (вместо удаления)."""
        employee.is_active = False
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def activate(self, employee: Employee) -> Employee:
        """Активировать сотрудника."""
        employee.is_active = True
        self.db.commit()
        self.db.refresh(employee)
        return employee
