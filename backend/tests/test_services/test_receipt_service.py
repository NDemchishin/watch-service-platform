"""Тесты сервиса квитанций (Issue #16)."""
import pytest
from datetime import datetime, timedelta

from app.models.receipt import Receipt
from app.models.history import HistoryEvent
from app.schemas.receipt import ReceiptCreate
from app.services.receipt_service import ReceiptService


class TestReceiptService:
    """Тесты ReceiptService."""

    def test_create_receipt(self, db_session):
        service = ReceiptService(db_session)
        data = ReceiptCreate(receipt_number="R-001")
        receipt = service.create(data, telegram_id=123, telegram_username="test")

        assert receipt.id is not None
        assert receipt.receipt_number == "R-001"

    def test_create_duplicate_raises(self, db_session):
        service = ReceiptService(db_session)
        service.create(ReceiptCreate(receipt_number="R-001"))
        with pytest.raises(ValueError):
            service.create(ReceiptCreate(receipt_number="R-001"))

    def test_create_receipt_logs_history(self, db_session):
        service = ReceiptService(db_session)
        receipt = service.create(ReceiptCreate(receipt_number="R-001"))

        events = db_session.query(HistoryEvent).filter_by(receipt_id=receipt.id).all()
        assert len(events) == 1
        assert events[0].event_type == "receipt_created"

    def test_get_by_id(self, db_session):
        service = ReceiptService(db_session)
        receipt = service.create(ReceiptCreate(receipt_number="R-001"))
        found = service.get_by_id(receipt.id)
        assert found is not None
        assert found.receipt_number == "R-001"

    def test_get_by_number(self, db_session):
        service = ReceiptService(db_session)
        service.create(ReceiptCreate(receipt_number="R-001"))
        found = service.get_by_number("R-001")
        assert found is not None

    def test_get_all(self, db_session):
        service = ReceiptService(db_session)
        service.create(ReceiptCreate(receipt_number="R-001"))
        service.create(ReceiptCreate(receipt_number="R-002"))
        all_receipts = service.get_all()
        assert len(all_receipts) == 2

    def test_update_deadline(self, db_session):
        service = ReceiptService(db_session)
        receipt = service.create(ReceiptCreate(receipt_number="R-001"))
        new_deadline = datetime(2099, 12, 31, 15, 0)

        updated = service.update_deadline(receipt, new_deadline, telegram_id=123)
        assert updated.current_deadline == new_deadline

    def test_update_deadline_logs_history(self, db_session):
        service = ReceiptService(db_session)
        receipt = service.create(ReceiptCreate(receipt_number="R-001"))
        service.update_deadline(receipt, datetime(2099, 12, 31, 15, 0))

        events = db_session.query(HistoryEvent).filter_by(
            receipt_id=receipt.id, event_type="deadline_changed"
        ).all()
        assert len(events) == 1

    def test_get_urgent(self, db_session):
        service = ReceiptService(db_session)
        # Квитанция с дедлайном - срочная
        r1 = service.create(ReceiptCreate(
            receipt_number="R-001",
            current_deadline=datetime(2099, 12, 31),
        ))
        # Квитанция без дедлайна - не срочная
        r2 = service.create(ReceiptCreate(receipt_number="R-002"))

        urgent = service.get_urgent()
        assert len(urgent) == 1
        assert urgent[0].receipt_number == "R-001"

    def test_get_urgent_excludes_passed_otk(self, db_session):
        service = ReceiptService(db_session)
        receipt = service.create(ReceiptCreate(
            receipt_number="R-001",
            current_deadline=datetime(2099, 12, 31),
        ))
        # Добавляем событие passed_otk
        event = HistoryEvent(
            receipt_id=receipt.id,
            event_type="passed_otk",
            payload={},
        )
        db_session.add(event)
        db_session.commit()

        urgent = service.get_urgent()
        assert len(urgent) == 0
