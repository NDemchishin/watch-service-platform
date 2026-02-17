"""
Сервис для работы с уведомлениями о дедлайнах.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.notification import Notification
from app.models.receipt import Receipt

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для управления уведомлениями."""

    def __init__(self, db: Session):
        self.db = db

    def schedule_notifications(self, receipt_id: int, deadline: datetime) -> list[Notification]:
        """
        Планирует уведомления при установке/изменении дедлайна.
        Создаёт 2 уведомления:
        - deadline_today: в 10:00 в день дедлайна
        - deadline_1h: за 1 час до дедлайна
        """
        # Сначала отменяем старые неотправленные уведомления
        self.cancel_notifications(receipt_id)

        notifications = []

        # Уведомление в 10:00 в день дедлайна
        day_start = deadline.replace(hour=10, minute=0, second=0, microsecond=0)
        if day_start > datetime.utcnow():
            notif_today = Notification(
                receipt_id=receipt_id,
                notification_type="deadline_today",
                scheduled_at=day_start,
            )
            self.db.add(notif_today)
            notifications.append(notif_today)

        # Уведомление за 1 час до дедлайна
        one_hour_before = deadline - timedelta(hours=1)
        if one_hour_before > datetime.utcnow():
            notif_1h = Notification(
                receipt_id=receipt_id,
                notification_type="deadline_1h",
                scheduled_at=one_hour_before,
            )
            self.db.add(notif_1h)
            notifications.append(notif_1h)

        self.db.flush()
        logger.info(f"Scheduled {len(notifications)} notifications for receipt {receipt_id}, deadline {deadline}")
        return notifications

    def cancel_notifications(self, receipt_id: int) -> int:
        """Отменяет все неотправленные уведомления для квитанции."""
        count = (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.receipt_id == receipt_id,
                    Notification.sent_at.is_(None),
                    Notification.is_cancelled == False,
                )
            )
            .update({"is_cancelled": True})
        )
        self.db.flush()
        if count:
            logger.info(f"Cancelled {count} notifications for receipt {receipt_id}")
        return count

    def get_pending(self) -> list[Notification]:
        """Получает неотправленные уведомления, время которых наступило."""
        now = datetime.utcnow()
        return (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.scheduled_at <= now,
                    Notification.sent_at.is_(None),
                    Notification.is_cancelled == False,
                )
            )
            .all()
        )

    def mark_sent(self, notification_id: int) -> None:
        """Отмечает уведомление как отправленное."""
        notif = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if notif:
            notif.sent_at = datetime.utcnow()
            self.db.flush()

    def get_receipt_for_notification(self, receipt_id: int) -> Optional[Receipt]:
        """Получает квитанцию для уведомления."""
        return self.db.query(Receipt).filter(Receipt.id == receipt_id).first()
