"""Тесты API квитанций (Issue #10)."""
from tests.conftest import create_receipt, create_employee


class TestReceiptsCRUD:
    """CRUD операции с квитанциями."""

    def test_create_receipt(self, client):
        resp = client.post("/api/v1/receipts", json={"receipt_number": "R-001"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["receipt_number"] == "R-001"
        assert data["id"] is not None

    def test_create_duplicate_receipt(self, client):
        client.post("/api/v1/receipts", json={"receipt_number": "R-001"})
        resp = client.post("/api/v1/receipts", json={"receipt_number": "R-001"})
        assert resp.status_code == 400

    def test_list_receipts_empty(self, client):
        resp = client.get("/api/v1/receipts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_receipts(self, client):
        create_receipt(client, "R-001")
        create_receipt(client, "R-002")
        resp = client.get("/api/v1/receipts")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_receipts_pagination(self, client):
        for i in range(5):
            create_receipt(client, f"R-{i:03d}")
        resp = client.get("/api/v1/receipts", params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    def test_get_receipt_by_id(self, client):
        created = create_receipt(client, "R-001")
        resp = client.get(f"/api/v1/receipts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["receipt_number"] == "R-001"

    def test_get_receipt_not_found(self, client):
        resp = client.get("/api/v1/receipts/9999")
        assert resp.status_code == 404

    def test_get_receipt_by_number(self, client):
        create_receipt(client, "R-001")
        resp = client.get("/api/v1/receipts/number/R-001")
        assert resp.status_code == 200
        assert resp.json()["receipt_number"] == "R-001"

    def test_get_receipt_by_number_not_found(self, client):
        resp = client.get("/api/v1/receipts/number/NONEXISTENT")
        assert resp.status_code == 404


class TestGetOrCreate:
    """Получение или создание квитанции."""

    def test_get_or_create_new(self, client):
        resp = client.post(
            "/api/v1/receipts/get-or-create",
            json={"receipt_number": "R-100"},
        )
        assert resp.status_code == 200
        assert resp.json()["receipt_number"] == "R-100"

    def test_get_or_create_existing(self, client):
        created = create_receipt(client, "R-100")
        resp = client.post(
            "/api/v1/receipts/get-or-create",
            json={"receipt_number": "R-100"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]


class TestDeadline:
    """Обновление дедлайна."""

    def test_update_deadline(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.patch(
            f"/api/v1/receipts/{receipt['id']}/deadline",
            json={"current_deadline": "2025-06-15T14:00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_deadline"] is not None

    def test_update_deadline_not_found(self, client):
        resp = client.patch(
            "/api/v1/receipts/9999/deadline",
            json={"current_deadline": "2025-06-15T14:00:00"},
        )
        assert resp.status_code == 404


class TestUrgent:
    """Список срочных часов."""

    def test_urgent_empty(self, client):
        resp = client.get("/api/v1/receipts/urgent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_urgent_with_deadline(self, client):
        receipt = create_receipt(client, "R-001")
        client.patch(
            f"/api/v1/receipts/{receipt['id']}/deadline",
            json={"current_deadline": "2099-12-31T23:59:00"},
        )
        resp = client.get("/api/v1/receipts/urgent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_urgent_excludes_passed_otk(self, client):
        receipt = create_receipt(client, "R-001")
        client.patch(
            f"/api/v1/receipts/{receipt['id']}/deadline",
            json={"current_deadline": "2099-12-31T23:59:00"},
        )
        # Отмечаем прохождение ОТК
        client.post(f"/api/v1/receipts/{receipt['id']}/otk-pass")
        resp = client.get("/api/v1/receipts/urgent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestAssignMaster:
    """Выдача часов мастеру."""

    def test_assign_master(self, client):
        receipt = create_receipt(client, "R-001")
        employee = create_employee(client, "Мастер Иван")
        resp = client.post(
            "/api/v1/receipts/assign-master",
            json={
                "receipt_id": receipt["id"],
                "master_id": employee["id"],
            },
        )
        assert resp.status_code == 200

    def test_assign_master_receipt_not_found(self, client):
        employee = create_employee(client, "Мастер Иван")
        resp = client.post(
            "/api/v1/receipts/assign-master",
            json={"receipt_id": 9999, "master_id": employee["id"]},
        )
        assert resp.status_code == 404

    def test_assign_master_employee_not_found(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.post(
            "/api/v1/receipts/assign-master",
            json={"receipt_id": receipt["id"], "master_id": 9999},
        )
        assert resp.status_code == 404


class TestOTKAndReturn:
    """Прохождение ОТК и инициация возврата."""

    def test_otk_pass(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.post(f"/api/v1/receipts/{receipt['id']}/otk-pass")
        assert resp.status_code == 200

    def test_otk_pass_not_found(self, client):
        resp = client.post("/api/v1/receipts/9999/otk-pass")
        assert resp.status_code == 404

    def test_initiate_return(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.post(f"/api/v1/receipts/{receipt['id']}/initiate-return")
        assert resp.status_code == 200

    def test_receipt_with_history(self, client):
        receipt = create_receipt(client, "R-001")
        resp = client.get(f"/api/v1/receipts/{receipt['id']}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        # При создании квитанции автоматически создаётся history event
        assert len(data["history"]) >= 1

    def test_receipt_creates_history_event(self, client):
        """Создание квитанции логируется в историю."""
        receipt = create_receipt(client, "R-001")
        resp = client.get(f"/api/v1/history/receipt/{receipt['id']}")
        assert resp.status_code == 200
        events = resp.json()["items"]
        assert any(e["event_type"] == "receipt_created" for e in events)
