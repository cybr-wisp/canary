
import hashlib
import hmac

import time
from pathlib import Path

import jwt

def verify_webhook_signature(
    payload: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """
    Verify that a webhook payload was signed using our GitHub webhook secret.
    """

    if not signature:
        return False

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

def create_app_jwt(
    app_id: str,
    private_key_path: str,
) -> str:
    """Create a short-lived JWT used to authenticate the GitHub App."""

    private_key = Path(private_key_path).read_text(
        encoding="utf-8"
    )

    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )