"""
Модель деталей полировки.
"""
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PolishingDetails(Base):
    """Детали передачи в полировку."""
    __tablename__ = "polishing_details"

    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), primary_key=True)
    polisher_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    metal_type: Mapped[str] = mapped_column(String, nullable=False)
    bracelet: Mapped[bool] = mapped_column(Boolean, default=False)
    difficult: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    returned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
