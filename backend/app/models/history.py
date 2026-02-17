"""
Модель истории событий.
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utils import now_moscow


class HistoryEvent(Base):
    """История всех событий в системе."""
    __tablename__ = "history_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    telegram_username: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_moscow)
