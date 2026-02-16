"""Тесты сервиса сотрудников (Issue #16)."""
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.employee_service import EmployeeService


class TestEmployeeService:
    """Тесты EmployeeService."""

    def test_create_employee(self, db_session):
        service = EmployeeService(db_session)
        data = EmployeeCreate(name="Иван", telegram_id=123)
        employee = service.create(data)
        assert employee.id is not None
        assert employee.name == "Иван"
        assert employee.is_active is True

    def test_get_by_id(self, db_session):
        service = EmployeeService(db_session)
        emp = service.create(EmployeeCreate(name="Иван"))
        found = service.get_by_id(emp.id)
        assert found is not None
        assert found.name == "Иван"

    def test_get_by_telegram_id(self, db_session):
        service = EmployeeService(db_session)
        service.create(EmployeeCreate(name="Иван", telegram_id=12345))
        found = service.get_by_telegram_id(12345)
        assert found is not None
        assert found.name == "Иван"

    def test_get_active(self, db_session):
        service = EmployeeService(db_session)
        emp1 = service.create(EmployeeCreate(name="Активный"))
        emp2 = service.create(EmployeeCreate(name="Неактивный"))
        service.deactivate(emp2)

        active = service.get_active()
        assert len(active) == 1
        assert active[0].name == "Активный"

    def test_get_inactive(self, db_session):
        service = EmployeeService(db_session)
        emp1 = service.create(EmployeeCreate(name="Активный"))
        emp2 = service.create(EmployeeCreate(name="Неактивный"))
        service.deactivate(emp2)

        inactive = service.get_inactive()
        assert len(inactive) == 1
        assert inactive[0].name == "Неактивный"

    def test_update(self, db_session):
        service = EmployeeService(db_session)
        emp = service.create(EmployeeCreate(name="Иван"))
        updated = service.update(emp, EmployeeUpdate(name="Пётр"))
        assert updated.name == "Пётр"

    def test_deactivate(self, db_session):
        service = EmployeeService(db_session)
        emp = service.create(EmployeeCreate(name="Иван"))
        deactivated = service.deactivate(emp)
        assert deactivated.is_active is False

    def test_activate(self, db_session):
        service = EmployeeService(db_session)
        emp = service.create(EmployeeCreate(name="Иван"))
        service.deactivate(emp)
        activated = service.activate(emp)
        assert activated.is_active is True
