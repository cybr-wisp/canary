import json

from fastapi import FastAPI, HTTPException, Request

from app.config import settings
from app.github.auth import verify_webhook_signature


app = FastAPI(
    title="Canary",
    description="Behavioral regression detection for GitHub pull requests",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "canary",
        "version": "0.1.0",
    }


@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.body()

    signature = request.headers.get("X-Hub-Signature-256")
    event = request.headers.get("X-GitHub-Event", "unknown")

    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="Webhook secret is not configured",
        )

    if not verify_webhook_signature(
        payload=payload,
        signature=signature,
        secret=settings.github_webhook_secret,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    if event == "ping":
        return {
            "status": "ok",
            "event": "ping",
        }

    if event == "pull_request":
        pr = data.get("pull_request", {})

        return {
            "status": "accepted",
            "event": "pull_request",
            "action": data.get("action"),
            "pull_request": {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
            },
        }

    return {
        "status": "ignored",
        "event": event,
    }