
import hashlib
import hmac


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