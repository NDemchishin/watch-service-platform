"""
Модель сотрудника.
"""
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utils import now_moscow


class Employee(Base):
    """Сотрудник мастерской."""
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="master")
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_moscow)
