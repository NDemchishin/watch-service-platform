"""
Модели операций и типов операций.
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import now_moscow


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
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False, index=True)
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_moscow)

    operation_type = relationship("OperationType", lazy="select")
    employee = relationship("Employee", lazy="select")
