import httpx

from app.config import settings
from app.github.client import GitHubClient
from app.github.presentation import build_check_output
from app.models import AnalysisResult


def determine_conclusion(result: AnalysisResult) -> str:
    """
    Determine the GitHub Check conclusion from Canary's analysis.

    No findings      -> success
    Low/medium only  -> neutral
    Any high finding -> failure
    """

    if result.finding_count == 0:
        return "success"

    if result.has_high_risk:
        return "failure"

    return "neutral"


async def create_canary_check(
    repository: str,
    head_sha: str,
    installation_id: int,
    result: AnalysisResult,
) -> None:
    """
    Publish Canary's analysis as a GitHub Check Run.
    """

    github = GitHubClient()

    installation_token = await github.get_installation_token(
        installation_id
    )

    conclusion = determine_conclusion(result)

    payload = {
        "name": "Canary",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": build_check_output(result),
    }

    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = (
        f"{settings.github_api_url.rstrip('/')}"
        f"/repos/{repository}/check-runs"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
            timeout=10.0,
        )

        response.raise_for_status()