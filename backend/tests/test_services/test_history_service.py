"""Тесты сервиса истории (Issue #16)."""
from app.models.receipt import Receipt
from app.schemas.history import HistoryEventCreate
from app.services.history_service import HistoryService


class TestHistoryService:
    """Тесты HistoryService."""

    def _create_receipt(self, db_session) -> Receipt:
        receipt = Receipt(receipt_number="R-001")
        db_session.add(receipt)
        db_session.commit()
        db_session.refresh(receipt)
        return receipt

    def test_create_event(self, db_session):
        receipt = self._create_receipt(db_session)
        service = HistoryService(db_session)
        event = service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="test_event",
            payload={"key": "value"},
        ))
        assert event.id is not None
        assert event.event_type == "test_event"

    def test_get_by_id(self, db_session):
        receipt = self._create_receipt(db_session)
        service = HistoryService(db_session)
        event = service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="test_event",
            payload={},
        ))
        found = service.get_by_id(event.id)
        assert found is not None

    def test_get_by_receipt(self, db_session):
        receipt = self._create_receipt(db_session)
        service = HistoryService(db_session)
        service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="event_1",
            payload={},
        ))
        service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="event_2",
            payload={},
        ))
        events = service.get_by_receipt(receipt.id)
        assert len(events) == 2

    def test_get_all_with_filter(self, db_session):
        receipt = self._create_receipt(db_session)
        service = HistoryService(db_session)
        service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="type_a",
            payload={},
        ))
        service.create(HistoryEventCreate(
            receipt_id=receipt.id,
            event_type="type_b",
            payload={},
        ))

        filtered = service.get_all(event_type="type_a")
        assert len(filtered) == 1
        assert filtered[0].event_type == "type_a"
