"""
Модели операций и типов операций.
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OperationType(Base):
    """Тип операции (сборка, механизм, полировка)."""
    __tablename__ = "operation_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Operation(Base):
    """Выполненная операция."""
    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    operation_type = relationship("OperationType", lazy="select")
    employee = relationship("Employee", lazy="select")
