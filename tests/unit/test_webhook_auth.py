
import hashlib
import hmac

from app.github.auth import verify_webhook_signature


SECRET = "canary-test-secret"
PAYLOAD = b'{"action":"opened","number":42}'


def make_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def test_valid_webhook_signature():
    signature = make_signature(PAYLOAD, SECRET)

    assert verify_webhook_signature(
        payload=PAYLOAD,
        signature=signature,
        secret=SECRET,
    )


def test_invalid_webhook_signature():
    fake_signature = "sha256=definitely-not-valid"

    assert not verify_webhook_signature(
        payload=PAYLOAD,
        signature=fake_signature,
        secret=SECRET,
    )


def test_missing_webhook_signature():
    assert not verify_webhook_signature(
        payload=PAYLOAD,
        signature=None,
        secret=SECRET,
    )