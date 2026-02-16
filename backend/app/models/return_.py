"""
Модели возвратов и причин возвратов.
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Return(Base):
    """Возврат часов."""
    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reasons = relationship("ReturnReasonLink", lazy="select")


class ReturnReason(Base):
    """Причина возврата."""
    __tablename__ = "return_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    affects: Mapped[str] = mapped_column(String, nullable=False)  # assembly / mechanism / polishing


class ReturnReasonLink(Base):
    """Связь возврата с причиной и виновным."""
    __tablename__ = "return_reason_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("returns.id"), nullable=False)
    reason_id: Mapped[int] = mapped_column(ForeignKey("return_reasons.id"), nullable=False)
    guilty_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=True)

    reason = relationship("ReturnReason", lazy="select")
    guilty_employee = relationship("Employee", lazy="select")
