"""Тесты API истории событий (Issue #15)."""
from tests.conftest import create_receipt


class TestHistoryCRUD:
    """CRUD операции с историей."""

    def test_list_history_empty(self, client):
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_create_history_event(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.post(
            "/api/v1/history",
            json={
                "receipt_id": receipt["id"],
                "event_type": "test_event",
                "payload": {"key": "value"},
                "telegram_id": 12345,
                "telegram_username": "testuser",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "test_event"
        assert data["payload"] == {"key": "value"}

    def test_get_history_event_by_id(self, client):
        receipt = create_receipt(client, "R-001")
        created = client.post(
            "/api/v1/history",
            json={
                "receipt_id": receipt["id"],
                "event_type": "test_event",
                "payload": {},
            },
        )
        event_id = created.json()["id"]
        resp = client.get(f"/api/v1/history/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "test_event"

    def test_get_history_event_not_found(self, client):
        resp = client.get("/api/v1/history/9999")
        assert resp.status_code == 404

    def test_get_history_by_receipt(self, client):
        receipt = create_receipt(client, "R-001")
        # При создании квитанции уже есть receipt_created
        resp = client.get(f"/api/v1/history/receipt/{receipt['id']}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_event_type(self, client):
        receipt = create_receipt(client, "R-001")
        client.post(
            "/api/v1/history",
            json={
                "receipt_id": receipt["id"],
                "event_type": "custom_type",
                "payload": {},
            },
        )

        resp = client.get("/api/v1/history", params={"event_type": "custom_type"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(e["event_type"] == "custom_type" for e in items)

    def test_history_pagination(self, client):
        receipt = create_receipt(client, "R-001")
        for i in range(5):
            client.post(
                "/api/v1/history",
                json={
                    "receipt_id": receipt["id"],
                    "event_type": f"event_{i}",
                    "payload": {},
                },
            )

        resp = client.get("/api/v1/history", params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2
