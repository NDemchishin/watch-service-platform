"""Тесты API полировки (Issue #13)."""
from tests.conftest import create_receipt, create_employee


def _create_polishing(client, receipt_id: int, polisher_id: int) -> dict:
    """Вспомогательная функция: создание записи полировки."""
    resp = client.post(
        "/api/v1/polishing",
        json={
            "receipt_id": receipt_id,
            "polisher_id": polisher_id,
            "metal_type": "gold",
            "bracelet": True,
            "difficult": False,
            "comment": "Тестовая полировка",
        },
    )
    assert resp.status_code == 201
    return resp.json()


class TestPolishingCRUD:
    """CRUD операции с полировкой."""

    def test_create_polishing(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        data = _create_polishing(client, receipt["id"], polisher["id"])
        assert data["receipt_id"] == receipt["id"]
        assert data["metal_type"] == "gold"
        assert data["bracelet"] is True
        assert data["returned_at"] is None

    def test_create_duplicate_polishing(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])
        resp = client.post(
            "/api/v1/polishing",
            json={
                "receipt_id": receipt["id"],
                "polisher_id": polisher["id"],
                "metal_type": "steel",
            },
        )
        assert resp.status_code == 400

    def test_get_polishing_by_receipt(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        resp = client.get(f"/api/v1/polishing/receipt/{receipt['id']}")
        assert resp.status_code == 200
        assert resp.json()["receipt_id"] == receipt["id"]

    def test_get_polishing_not_found(self, client):
        resp = client.get("/api/v1/polishing/receipt/9999")
        assert resp.status_code == 404

    def test_list_in_progress(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        resp = client.get("/api/v1/polishing/in-progress")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestPolishingReturn:
    """Возврат из полировки."""

    def test_mark_returned(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        resp = client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})
        assert resp.status_code == 200
        assert resp.json()["returned_at"] is not None

    def test_return_not_found(self, client):
        resp = client.post("/api/v1/polishing/receipt/9999/return", json={})
        assert resp.status_code == 404

    def test_double_return(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})
        resp = client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})
        assert resp.status_code == 400

    def test_returned_not_in_progress(self, client):
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})

        resp = client.get("/api/v1/polishing/in-progress")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestPolishingStats:
    """Статистика полировщика."""

    def test_stats(self, client):
        polisher = create_employee(client, "Полировщик")
        resp = client.get(f"/api/v1/polishing/stats/{polisher['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["polisher_id"] == polisher["id"]
        assert data["in_progress"] == 0

    def test_polishing_creates_history(self, client):
        """Передача в полировку логируется в историю."""
        receipt = create_receipt(client, "R-001")
        polisher = create_employee(client, "Полировщик")
        _create_polishing(client, receipt["id"], polisher["id"])

        resp = client.get(f"/api/v1/history/receipt/{receipt['id']}")
        events = resp.json()["items"]
        assert any(e["event_type"] == "polishing_sent" for e in events)
