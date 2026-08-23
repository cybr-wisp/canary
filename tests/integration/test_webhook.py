import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)

SECRET = "canary-test-secret"


def sign(payload: bytes) -> str:
    digest = hmac.new(
        SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def test_pull_request_webhook():
    settings.github_webhook_secret = SECRET

    body = {
        "action": "opened",
        "repository": {
            "full_name": "cybr-wisp/canary-testbed",
        },
        "installation": {
            "id": 12345,
        },
        "pull_request": {
            "number": 42,
            "title": "Test Canary",
            "state": "open",
            "head": {
                "sha": "abc123",
            },
        },
    }

    payload = json.dumps(body).encode("utf-8")

    with patch(
        "app.main.analyze_pull_request",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.main.create_canary_check",
        new=AsyncMock(),
    ):
        response = client.post(
            "/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sign(payload),
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "analyzed"
    assert data["repository"] == "cybr-wisp/canary-testbed"
    assert data["pull_request"] == 42
    assert data["findings"] == 0


def test_webhook_rejects_invalid_signature():
    settings.github_webhook_secret = SECRET

    response = client.post(
        "/webhook",
        content=b'{"action":"opened"}',
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=fake",
        },
    )

    assert response.status_code == 401