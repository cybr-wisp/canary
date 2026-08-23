import json

from fastapi import FastAPI, HTTPException, Request

from app.config import settings
from app.github.auth import verify_webhook_signature
from app.github.checks import create_canary_check
from app.services.pr_analysis import analyze_pull_request


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

    if event != "pull_request":
        return {
            "status": "ignored",
            "event": event,
        }

    action = data.get("action")

    if action not in {
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    }:
        return {
            "status": "ignored",
            "event": event,
            "action": action,
        }

    repository = data["repository"]["full_name"]
    pull_number = data["pull_request"]["number"]
    installation_id = data["installation"]["id"]
    head_sha = data["pull_request"]["head"]["sha"]

    findings = await analyze_pull_request(
        repository=repository,
        pull_number=pull_number,
        installation_id=installation_id,
    )

    await create_canary_check(
        repository=repository,
        head_sha=head_sha,
        installation_id=installation_id,
        findings=findings,
    )

    return {
        "status": "analyzed",
        "repository": repository,
        "pull_request": pull_number,
        "findings": len(findings),
    }