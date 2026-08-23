
from fastapi import FastAPI

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