"""
Pydantic схемы для уведомлений.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """Схема ответа с данными уведомления."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int
    notification_type: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    is_cancelled: bool = False
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Схема списка уведомлений."""
    items: list[NotificationResponse]
    total: int
