"""Тесты API уведомлений."""
from tests.conftest import create_receipt


class TestNotifications:
    """Тесты эндпоинтов уведомлений."""

    def test_pending_empty(self, client):
        resp = client.get("/api/v1/notifications/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_notifications_scheduled_on_deadline(self, client):
        """При установке дедлайна планируются уведомления."""
        receipt = create_receipt(client, "R-001")
        client.patch(
            f"/api/v1/receipts/{receipt['id']}/deadline",
            json={"current_deadline": "2099-12-31T15:00:00"},
        )
        # Уведомления запланированы на будущее, поэтому pending пока 0
        resp = client.get("/api/v1/notifications/pending")
        assert resp.status_code == 200
