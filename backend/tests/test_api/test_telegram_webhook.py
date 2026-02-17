"""
Тесты верификации секрета Telegram webhook.
"""


def test_webhook_without_secret_returns_403(client):
    """Webhook without secret header should return 403."""
    response = client.post(
        "/webhook/telegram/webhook",
        json={"update_id": 1}
    )
    assert response.status_code == 403


def test_webhook_with_valid_secret(client):
    """Webhook with valid secret should not return 403."""
    response = client.post(
        "/webhook/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}
    )
    # Should not be 403 (may be other error due to invalid update, but not auth error)
    assert response.status_code != 403


def test_webhook_with_wrong_secret_returns_403(client):
    """Webhook with wrong secret should return 403."""
    response = client.post(
        "/webhook/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"}
    )
    assert response.status_code == 403
