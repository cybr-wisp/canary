
import hashlib
import hmac
import json

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
        "pull_request": {
            "number": 42,
            "title": "Fix authentication fallback",
            "state": "open",
        },
    }

    payload = json.dumps(body).encode("utf-8")

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

    assert data["status"] == "accepted"
    assert data["action"] == "opened"
    assert data["pull_request"]["number"] == 42


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