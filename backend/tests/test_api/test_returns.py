"""Тесты API возвратов (Issue #14)."""
from tests.conftest import create_receipt, create_employee


class TestReturnReasons:
    """Причины возвратов."""

    def test_list_reasons_empty(self, client):
        resp = client.get("/api/v1/returns/reasons")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_reasons_seeded(self, seeded_client):
        resp = seeded_client.get("/api/v1/returns/reasons")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        codes = {r["code"] for r in data["items"]}
        assert "dirt_inside" in codes
        assert "polishing" in codes

    def test_get_reason_by_code(self, seeded_client):
        resp = seeded_client.get("/api/v1/returns/reasons/dirt_inside")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "dirt_inside"
        assert data["affects"] == "assembly"

    def test_get_reason_not_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/returns/reasons/nonexistent")
        assert resp.status_code == 404


class TestReturnsCRUD:
    """CRUD операции с возвратами."""

    def test_create_return(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        # Берём ID причины
        reasons_resp = seeded_client.get("/api/v1/returns/reasons/dirt_inside")
        reason_id = reasons_resp.json()["id"]

        resp = seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "comment": "Тестовый возврат",
                "reasons": [{"reason_id": reason_id}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["receipt_id"] == receipt["id"]
        assert data["comment"] == "Тестовый возврат"

    def test_create_return_with_guilty(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        employee = create_employee(seeded_client, "Виновный Мастер")
        reasons_resp = seeded_client.get("/api/v1/returns/reasons/dirt_inside")
        reason_id = reasons_resp.json()["id"]

        resp = seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "reasons": [
                    {"reason_id": reason_id, "guilty_employee_id": employee["id"]},
                ],
            },
        )
        assert resp.status_code == 201

    def test_create_return_multiple_reasons(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        r1 = seeded_client.get("/api/v1/returns/reasons/dirt_inside").json()
        r2 = seeded_client.get("/api/v1/returns/reasons/mechanism_defect").json()

        resp = seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "reasons": [
                    {"reason_id": r1["id"]},
                    {"reason_id": r2["id"]},
                ],
            },
        )
        assert resp.status_code == 201

    def test_list_returns_empty(self, client):
        resp = client.get("/api/v1/returns")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_returns_by_receipt(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        reason = seeded_client.get("/api/v1/returns/reasons/dirt_inside").json()

        seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "reasons": [{"reason_id": reason["id"]}],
            },
        )

        resp = seeded_client.get(f"/api/v1/returns/receipt/{receipt['id']}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_return_by_id(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        reason = seeded_client.get("/api/v1/returns/reasons/dirt_inside").json()

        created = seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "reasons": [{"reason_id": reason["id"]}],
            },
        )
        return_id = created.json()["id"]

        resp = seeded_client.get(f"/api/v1/returns/{return_id}")
        assert resp.status_code == 200

    def test_get_return_not_found(self, client):
        resp = client.get("/api/v1/returns/9999")
        assert resp.status_code == 404

    def test_return_creates_history(self, seeded_client):
        """Создание возврата логируется в историю."""
        receipt = create_receipt(seeded_client, "R-001")
        reason = seeded_client.get("/api/v1/returns/reasons/dirt_inside").json()

        seeded_client.post(
            "/api/v1/returns",
            json={
                "receipt_id": receipt["id"],
                "reasons": [{"reason_id": reason["id"]}],
            },
        )

        resp = seeded_client.get(f"/api/v1/history/receipt/{receipt['id']}")
        events = resp.json()["items"]
        assert any(e["event_type"] == "return_created" for e in events)
