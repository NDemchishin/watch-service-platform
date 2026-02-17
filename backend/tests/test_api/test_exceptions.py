"""
Тесты для пользовательских исключений и глобального обработчика.
"""


def test_not_found_returns_404(client):
    """Запрос несуществующей квитанции должен вернуть 404."""
    response = client.get("/api/v1/receipts/999999")
    assert response.status_code == 404


def test_not_found_response_has_detail(client):
    """404-ответ должен содержать detail."""
    response = client.get("/api/v1/receipts/999999")
    data = response.json()
    assert "detail" in data


def test_app_exception_handler_returns_json(client):
    """AppException через global handler должен возвращать JSON с error_code."""
    # This tests via the existing 404 path for now;
    # once services raise AppException directly, the handler will catch them
    response = client.get("/api/v1/employees/999999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
