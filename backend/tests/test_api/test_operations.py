"""Тесты API операций (Issue #12)."""
from tests.conftest import create_receipt, create_employee


class TestOperationTypes:
    """Типы операций."""

    def test_list_types_empty(self, client):
        resp = client.get("/api/v1/operations/types")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_types_seeded(self, seeded_client):
        resp = seeded_client.get("/api/v1/operations/types")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        codes = {t["code"] for t in data["items"]}
        assert codes == {"assembly", "mechanism", "polishing"}

    def test_get_type_by_code(self, seeded_client):
        resp = seeded_client.get("/api/v1/operations/types/assembly")
        assert resp.status_code == 200
        assert resp.json()["code"] == "assembly"

    def test_get_type_not_found(self, seeded_client):
        resp = seeded_client.get("/api/v1/operations/types/nonexistent")
        assert resp.status_code == 404


class TestOperationsCRUD:
    """CRUD операции."""

    def test_create_operation(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        employee = create_employee(seeded_client, "Мастер")
        # Берём ID типа assembly
        types_resp = seeded_client.get("/api/v1/operations/types/assembly")
        type_id = types_resp.json()["id"]

        resp = seeded_client.post(
            "/api/v1/operations",
            json={
                "receipt_id": receipt["id"],
                "operation_type_id": type_id,
                "employee_id": employee["id"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["receipt_id"] == receipt["id"]
        assert data["employee_id"] == employee["id"]

    def test_list_operations_empty(self, client):
        resp = client.get("/api/v1/operations")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_operations_by_receipt(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        employee = create_employee(seeded_client, "Мастер")
        types_resp = seeded_client.get("/api/v1/operations/types/assembly")
        type_id = types_resp.json()["id"]

        seeded_client.post(
            "/api/v1/operations",
            json={
                "receipt_id": receipt["id"],
                "operation_type_id": type_id,
                "employee_id": employee["id"],
            },
        )

        resp = seeded_client.get(f"/api/v1/operations/receipt/{receipt['id']}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_operation_by_id(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        employee = create_employee(seeded_client, "Мастер")
        types_resp = seeded_client.get("/api/v1/operations/types/assembly")
        type_id = types_resp.json()["id"]

        created = seeded_client.post(
            "/api/v1/operations",
            json={
                "receipt_id": receipt["id"],
                "operation_type_id": type_id,
                "employee_id": employee["id"],
            },
        )
        op_id = created.json()["id"]
        resp = seeded_client.get(f"/api/v1/operations/{op_id}")
        assert resp.status_code == 200

    def test_get_operation_not_found(self, client):
        resp = client.get("/api/v1/operations/9999")
        assert resp.status_code == 404

    def test_operation_creates_history(self, seeded_client):
        """Создание операции логируется в историю."""
        receipt = create_receipt(seeded_client, "R-001")
        employee = create_employee(seeded_client, "Мастер")
        types_resp = seeded_client.get("/api/v1/operations/types/assembly")
        type_id = types_resp.json()["id"]

        seeded_client.post(
            "/api/v1/operations",
            json={
                "receipt_id": receipt["id"],
                "operation_type_id": type_id,
                "employee_id": employee["id"],
            },
        )

        resp = seeded_client.get(f"/api/v1/history/receipt/{receipt['id']}")
        events = resp.json()["items"]
        assert any(e["event_type"] == "operation_created" for e in events)
