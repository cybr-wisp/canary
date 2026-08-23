
from app.analysis.analyzer import analyze_file
from app.github.client import GitHubClient
from app.models import RiskFinding


async def analyze_pull_request(
    repository: str,
    pull_number: int,
    installation_id: int,
) -> list[RiskFinding]:
    """Fetch and analyze every changed file in a pull request."""

    client = GitHubClient()

    changed_files = await client.get_pull_request_files(
        repository=repository,
        pull_number=pull_number,
        installation_id=installation_id,
    )

    findings: list[RiskFinding] = []

    for changed_file in changed_files:
        findings.extend(analyze_file(changed_file))

    return findings