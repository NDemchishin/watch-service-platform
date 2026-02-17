"""
Тесты аутентификации API ключом.
"""


def test_unauthenticated_request_returns_401(client_no_auth):
    """Request without API key should return 401."""
    response = client_no_auth.get("/api/v1/receipts")
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_authenticated_request_succeeds(client):
    """Request with valid API key should succeed."""
    response = client.get("/api/v1/receipts")
    assert response.status_code == 200


def test_wrong_api_key_returns_401(client_no_auth):
    """Request with wrong API key should return 401."""
    response = client_no_auth.get(
        "/api/v1/receipts",
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
