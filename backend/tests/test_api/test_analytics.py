"""Тесты API аналитики (Sprint 6, Issues #28-#32)."""
from tests.conftest import create_receipt, create_employee


def _get_type_id(client, code: str) -> int:
    """Вспомогательная — получить ID типа операции по коду."""
    resp = client.get(f"/api/v1/operations/types/{code}")
    return resp.json()["id"]


def _get_reason_id(client, code: str) -> int:
    """Вспомогательная — получить ID причины возврата по коду."""
    resp = client.get(f"/api/v1/returns/reasons/{code}")
    return resp.json()["id"]


def _create_operation(client, receipt_id: int, employee_id: int, type_code: str):
    """Создать операцию."""
    type_id = _get_type_id(client, type_code)
    resp = client.post(
        "/api/v1/operations",
        json={
            "receipt_id": receipt_id,
            "operation_type_id": type_id,
            "employee_id": employee_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_return(client, receipt_id: int, reason_code: str, guilty_employee_id=None):
    """Создать возврат с одной причиной."""
    reason_id = _get_reason_id(client, reason_code)
    reason_data = {"reason_id": reason_id}
    if guilty_employee_id:
        reason_data["guilty_employee_id"] = guilty_employee_id
    resp = client.post(
        "/api/v1/returns",
        json={
            "receipt_id": receipt_id,
            "reasons": [reason_data],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_polishing(client, receipt_id: int, polisher_id: int):
    """Создать запись полировки."""
    resp = client.post(
        "/api/v1/polishing",
        json={
            "receipt_id": receipt_id,
            "polisher_id": polisher_id,
            "metal_type": "gold",
            "bracelet": False,
            "difficult": False,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ========== Issue #28: Качество сборки ==========

class TestAssemblyQuality:
    """Тесты качества сборки."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/quality/assembly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "all"
        assert data["employees"] == []

    def test_100_percent_quality(self, seeded_client):
        """Сотрудник без возвратов — 100% качества."""
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Сборщик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")

        resp = seeded_client.get("/api/v1/analytics/quality/assembly")
        data = resp.json()
        assert len(data["employees"]) == 1
        assert data["employees"][0]["total_operations"] == 1
        assert data["employees"][0]["total_returns"] == 0
        assert data["employees"][0]["quality_percent"] == 100.0

    def test_quality_with_assembly_return(self, seeded_client):
        """Возврат по сборке снижает качество."""
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Сборщик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")
        _create_return(seeded_client, receipt["id"], "dirt_inside")

        resp = seeded_client.get("/api/v1/analytics/quality/assembly")
        data = resp.json()
        assert len(data["employees"]) == 1
        assert data["employees"][0]["total_returns"] == 1
        assert data["employees"][0]["quality_percent"] == 0.0

    def test_mechanism_return_does_not_affect_assembly(self, seeded_client):
        """Возврат по механизму НЕ портит качество сборки (по ТЗ)."""
        receipt = create_receipt(seeded_client, "R-001")
        assembler = create_employee(seeded_client, "Сборщик")
        mechanic = create_employee(seeded_client, "Механик")
        _create_operation(seeded_client, receipt["id"], assembler["id"], "assembly")
        _create_operation(seeded_client, receipt["id"], mechanic["id"], "mechanism")
        _create_return(seeded_client, receipt["id"], "mechanism_defect")

        resp = seeded_client.get("/api/v1/analytics/quality/assembly")
        data = resp.json()
        assembler_stats = [
            e for e in data["employees"] if e["employee_id"] == assembler["id"]
        ]
        assert len(assembler_stats) == 1
        assert assembler_stats[0]["total_returns"] == 0
        assert assembler_stats[0]["quality_percent"] == 100.0

    def test_filter_by_period(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/quality/assembly?period=day")
        assert resp.status_code == 200
        assert resp.json()["period"] == "day"

    def test_filter_by_employee(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Сборщик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")

        resp = seeded_client.get(
            f"/api/v1/analytics/quality/assembly?employee_id={emp['id']}"
        )
        data = resp.json()
        assert len(data["employees"]) == 1
        assert data["employees"][0]["employee_id"] == emp["id"]


# ========== Issue #29: Качество механизма ==========

class TestMechanismQuality:
    """Тесты качества механизма."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/quality/mechanism")
        assert resp.status_code == 200
        assert resp.json()["employees"] == []

    def test_mechanism_quality(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Механик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "mechanism")
        _create_return(seeded_client, receipt["id"], "mechanism_defect")

        resp = seeded_client.get("/api/v1/analytics/quality/mechanism")
        data = resp.json()
        assert len(data["employees"]) == 1
        assert data["employees"][0]["total_returns"] == 1
        assert data["employees"][0]["quality_percent"] == 0.0

    def test_assembly_return_does_not_affect_mechanism(self, seeded_client):
        """Возврат по сборке не портит качество механизма."""
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Механик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "mechanism")
        _create_return(seeded_client, receipt["id"], "dirt_inside")

        resp = seeded_client.get("/api/v1/analytics/quality/mechanism")
        data = resp.json()
        assert data["employees"][0]["total_returns"] == 0
        assert data["employees"][0]["quality_percent"] == 100.0


# ========== Issue #30: Качество полировки ==========

class TestPolishingQuality:
    """Тесты качества полировки."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/quality/polishing")
        assert resp.status_code == 200
        assert resp.json()["polishers"] == []

    def test_polishing_quality_with_guilty(self, seeded_client):
        """Качество полировки учитывает виновного из ReturnReasonLink."""
        receipt = create_receipt(seeded_client, "R-001")
        polisher = create_employee(seeded_client, "Полировщик")
        _create_polishing(seeded_client, receipt["id"], polisher["id"])
        # Помечаем как возвращённую из полировки
        seeded_client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})

        # Создаём возврат с причиной "полировка" и виновным = полировщик
        _create_return(
            seeded_client, receipt["id"], "polishing", guilty_employee_id=polisher["id"]
        )

        resp = seeded_client.get("/api/v1/analytics/quality/polishing")
        data = resp.json()
        assert len(data["polishers"]) == 1
        assert data["polishers"][0]["total_polished"] == 1
        assert data["polishers"][0]["total_returns"] == 1
        assert data["polishers"][0]["quality_percent"] == 0.0


# ========== Issue #31: Загрузка полировщиков ==========

class TestPolishingWorkload:
    """Тесты загрузки полировщиков."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/polishing/workload")
        assert resp.status_code == 200
        assert resp.json()["polishers"] == []

    def test_workload_in_progress(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        polisher = create_employee(seeded_client, "Полировщик")
        _create_polishing(seeded_client, receipt["id"], polisher["id"])

        resp = seeded_client.get("/api/v1/analytics/polishing/workload")
        data = resp.json()
        assert len(data["polishers"]) == 1
        p = data["polishers"][0]
        assert p["in_progress"] == 1
        assert p["completed"] == 0
        assert p["simple_count"] == 1
        assert p["difficult_count"] == 0

    def test_workload_completed(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        polisher = create_employee(seeded_client, "Полировщик")
        _create_polishing(seeded_client, receipt["id"], polisher["id"])
        seeded_client.post(f"/api/v1/polishing/receipt/{receipt['id']}/return", json={})

        resp = seeded_client.get("/api/v1/analytics/polishing/workload")
        data = resp.json()
        p = data["polishers"][0]
        assert p["in_progress"] == 0
        assert p["completed"] == 1

    def test_workload_breakdown(self, seeded_client):
        """Проверка breakdown по сложности и браслету."""
        r1 = create_receipt(seeded_client, "R-001")
        r2 = create_receipt(seeded_client, "R-002")
        polisher = create_employee(seeded_client, "Полировщик")

        # Простая без браслета
        _create_polishing(seeded_client, r1["id"], polisher["id"])

        # Сложная с браслетом
        seeded_client.post(
            "/api/v1/polishing",
            json={
                "receipt_id": r2["id"],
                "polisher_id": polisher["id"],
                "metal_type": "silver",
                "bracelet": True,
                "difficult": True,
            },
        )

        resp = seeded_client.get("/api/v1/analytics/polishing/workload")
        p = resp.json()["polishers"][0]
        assert p["simple_count"] == 1
        assert p["difficult_count"] == 1
        assert p["with_bracelet"] == 1
        assert p["without_bracelet"] == 1


# ========== Issue #32: Производительность ==========

class TestPerformance:
    """Тесты производительности."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_operations"] == 0

    def test_performance_grouped(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Мастер")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")
        _create_operation(seeded_client, receipt["id"], emp["id"], "mechanism")

        resp = seeded_client.get("/api/v1/analytics/performance")
        data = resp.json()
        assert data["total_operations"] == 2
        assert data["total_assembly"] == 1
        assert data["total_mechanism"] == 1
        assert len(data["employees"]) == 1
        assert data["employees"][0]["assembly_count"] == 1
        assert data["employees"][0]["mechanism_count"] == 1

    def test_performance_period_filter(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/performance?period=week")
        assert resp.status_code == 200
        assert resp.json()["period"] == "week"


# ========== Issue #32: Сводка возвратов ==========

class TestReturnsSummary:
    """Тесты сводки возвратов."""

    def test_empty(self, seeded_client):
        resp = seeded_client.get("/api/v1/analytics/returns/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_returns"] == 0
        assert data["by_reason"] == []

    def test_returns_by_reason(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Сборщик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")
        _create_return(seeded_client, receipt["id"], "dirt_inside")
        _create_return(seeded_client, receipt["id"], "wrong_assembly")

        resp = seeded_client.get("/api/v1/analytics/returns/summary")
        data = resp.json()
        assert data["total_returns"] == 2
        assert len(data["by_reason"]) == 2

    def test_top_employees(self, seeded_client):
        receipt = create_receipt(seeded_client, "R-001")
        emp = create_employee(seeded_client, "Сборщик")
        _create_operation(seeded_client, receipt["id"], emp["id"], "assembly")
        _create_return(seeded_client, receipt["id"], "dirt_inside")

        resp = seeded_client.get("/api/v1/analytics/returns/summary")
        data = resp.json()
        assert len(data["top_employees"]) == 1
        assert data["top_employees"][0]["employee_name"] == "Сборщик"
