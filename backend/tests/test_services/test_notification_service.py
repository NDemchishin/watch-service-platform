"""Тесты сервиса уведомлений (Issue #16)."""
from datetime import datetime, timedelta

from app.models.receipt import Receipt
from app.models.notification import Notification
from app.services.notification_service import NotificationService
from app.core.utils import now_moscow


class TestNotificationService:
    """Тесты NotificationService."""

    def _create_receipt(self, db_session) -> Receipt:
        receipt = Receipt(receipt_number="R-001")
        db_session.add(receipt)
        db_session.commit()
        db_session.refresh(receipt)
        return receipt

    def test_schedule_notifications(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)
        deadline = now_moscow() + timedelta(days=2)

        notifications = service.schedule_notifications(receipt.id, deadline)
        assert len(notifications) == 2
        types = {n.notification_type for n in notifications}
        assert types == {"deadline_today", "deadline_1h"}

    def test_cancel_notifications(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)
        deadline = now_moscow() + timedelta(days=2)
        service.schedule_notifications(receipt.id, deadline)

        count = service.cancel_notifications(receipt.id)
        assert count == 2

        # Проверяем что уведомления отменены
        all_notifs = db_session.query(Notification).all()
        assert all(n.is_cancelled for n in all_notifs)

    def test_get_pending(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)

        # Создаём уведомление в прошлом (уже должно быть отправлено)
        past_notif = Notification(
            receipt_id=receipt.id,
            notification_type="deadline_today",
            scheduled_at=now_moscow() - timedelta(hours=1),
        )
        db_session.add(past_notif)
        db_session.commit()

        pending = service.get_pending()
        assert len(pending) == 1

    def test_get_pending_excludes_sent(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)

        notif = Notification(
            receipt_id=receipt.id,
            notification_type="deadline_today",
            scheduled_at=now_moscow() - timedelta(hours=1),
            sent_at=now_moscow(),  # Уже отправлено
        )
        db_session.add(notif)
        db_session.commit()

        pending = service.get_pending()
        assert len(pending) == 0

    def test_get_pending_excludes_cancelled(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)

        notif = Notification(
            receipt_id=receipt.id,
            notification_type="deadline_today",
            scheduled_at=now_moscow() - timedelta(hours=1),
            is_cancelled=True,
        )
        db_session.add(notif)
        db_session.commit()

        pending = service.get_pending()
        assert len(pending) == 0

    def test_mark_sent(self, db_session):
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)

        notif = Notification(
            receipt_id=receipt.id,
            notification_type="deadline_today",
            scheduled_at=now_moscow() - timedelta(hours=1),
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        service.mark_sent(notif.id)
        db_session.refresh(notif)
        assert notif.sent_at is not None

    def test_reschedule_on_deadline_change(self, db_session):
        """При изменении дедлайна старые уведомления отменяются, новые создаются."""
        receipt = self._create_receipt(db_session)
        service = NotificationService(db_session)

        deadline1 = now_moscow() + timedelta(days=2)
        service.schedule_notifications(receipt.id, deadline1)

        deadline2 = now_moscow() + timedelta(days=5)
        new_notifs = service.schedule_notifications(receipt.id, deadline2)

        # Старые отменены, новые созданы
        all_notifs = db_session.query(Notification).filter_by(receipt_id=receipt.id).all()
        cancelled = [n for n in all_notifs if n.is_cancelled]
        active = [n for n in all_notifs if not n.is_cancelled]
        assert len(cancelled) == 2
        assert len(active) == 2
