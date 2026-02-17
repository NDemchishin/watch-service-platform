"""Smoke-тест: проверка инфраструктуры."""


def test_health_check(client):
    """Health endpoint отвечает 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_database_tables_created(db_session):
    """Таблицы создаются корректно."""
    from app.models.receipt import Receipt
    result = db_session.query(Receipt).all()
    assert result == []
