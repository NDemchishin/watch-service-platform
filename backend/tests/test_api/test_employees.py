"""Тесты API сотрудников (Issue #11)."""
from tests.conftest import create_employee


class TestEmployeesCRUD:
    """CRUD операции с сотрудниками."""

    def test_create_employee(self, client):
        resp = client.post(
            "/api/v1/employees",
            json={"name": "Иван Иванов", "role": "master", "telegram_id": 123456},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Иван Иванов"
        assert data["role"] == "master"
        assert data["telegram_id"] == 123456
        assert data["is_active"] is True

    def test_list_employees_empty(self, client):
        resp = client.get("/api/v1/employees")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_employees(self, client):
        create_employee(client, "Мастер 1")
        create_employee(client, "Мастер 2")
        resp = client.get("/api/v1/employees")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_get_employee_by_id(self, client):
        emp = create_employee(client, "Иван")
        resp = client.get(f"/api/v1/employees/{emp['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Иван"

    def test_get_employee_not_found(self, client):
        resp = client.get("/api/v1/employees/9999")
        assert resp.status_code == 404

    def test_get_employee_by_telegram_id(self, client):
        create_employee(client, "Иван", telegram_id=111222)
        resp = client.get("/api/v1/employees/telegram/111222")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Иван"

    def test_get_employee_by_telegram_not_found(self, client):
        resp = client.get("/api/v1/employees/telegram/999999")
        assert resp.status_code == 404

    def test_update_employee(self, client):
        emp = create_employee(client, "Иван")
        resp = client.patch(
            f"/api/v1/employees/{emp['id']}",
            json={"name": "Иван Петрович"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Иван Петрович"

    def test_update_employee_not_found(self, client):
        resp = client.patch(
            "/api/v1/employees/9999",
            json={"name": "Test"},
        )
        assert resp.status_code == 404


class TestEmployeeActivation:
    """Активация/деактивация сотрудников."""

    def test_deactivate_employee(self, client):
        emp = create_employee(client, "Иван")
        resp = client.post(f"/api/v1/employees/{emp['id']}/deactivate")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_activate_employee(self, client):
        emp = create_employee(client, "Иван")
        client.post(f"/api/v1/employees/{emp['id']}/deactivate")
        resp = client.post(f"/api/v1/employees/{emp['id']}/activate")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    def test_deactivate_not_found(self, client):
        resp = client.post("/api/v1/employees/9999/deactivate")
        assert resp.status_code == 404

    def test_filter_active_only(self, client):
        emp1 = create_employee(client, "Активный")
        emp2 = create_employee(client, "Неактивный")
        client.post(f"/api/v1/employees/{emp2['id']}/deactivate")

        resp = client.get("/api/v1/employees", params={"active_only": True})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Активный"

    def test_filter_inactive_only(self, client):
        emp1 = create_employee(client, "Активный")
        emp2 = create_employee(client, "Неактивный")
        client.post(f"/api/v1/employees/{emp2['id']}/deactivate")

        resp = client.get("/api/v1/employees", params={"inactive_only": True})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "Неактивный"
