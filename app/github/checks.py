import httpx

from app.config import settings
from app.github.client import GitHubClient
from app.models import RiskFinding, Severity


def determine_conclusion(findings: list[RiskFinding]) -> str:
    """
    Determine the GitHub Check conclusion from Canary findings.

    No findings      -> success
    Low/medium only  -> neutral
    Any high finding -> failure
    """

    if not findings:
        return "success"

    if any(
        finding.severity == Severity.HIGH
        for finding in findings
    ):
        return "failure"

    return "neutral"


def build_check_summary(findings: list[RiskFinding]) -> str:
    """Build the high-level Markdown summary shown in GitHub Checks."""

    if not findings:
        return (
            "## ✅ Canary passed\n\n"
            "No deterministic behavioral regression risks were detected."
        )

    high = sum(
        finding.severity == Severity.HIGH
        for finding in findings
    )

    medium = sum(
        finding.severity == Severity.MEDIUM
        for finding in findings
    )

    low = sum(
        finding.severity == Severity.LOW
        for finding in findings
    )

    if high:
        overall_risk = "🔴 HIGH"
    elif medium:
        overall_risk = "🟡 MEDIUM"
    else:
        overall_risk = "🔵 LOW"

    return (
        "## 🐤 Canary detected a regression signal\n\n"
        f"**Overall risk: {overall_risk}**\n\n"
        "| Severity | Findings |\n"
        "| --- | ---: |\n"
        f"| 🔴 High | {high} |\n"
        f"| 🟡 Medium | {medium} |\n"
        f"| 🔵 Low | {low} |\n\n"
        f"**Total:** {len(findings)} potential regression risk(s)"
    )


def build_check_text(findings: list[RiskFinding]) -> str:
    """Build detailed Markdown explaining each regression finding."""

    if not findings:
        return (
            "### ✅ No issues found\n\n"
            "Canary found no deterministic behavioral regression signals."
        )

    icons = {
        Severity.HIGH: "🔴",
        Severity.MEDIUM: "🟡",
        Severity.LOW: "🔵",
    }

    sections: list[str] = []

    for finding in findings:
        icon = icons[finding.severity]

        section = (
            f"### {icon} "
            f"{finding.severity.value.upper()} · "
            f"{finding.category}\n\n"
            f"**File:** `{finding.filename}`"
        )

        if finding.line is not None:
            section += f" · **Line:** `{finding.line}`"

        section += f"\n\n{finding.message}"

        if finding.evidence:
            section += (
                "\n\n"
                "**Detected change**\n\n"
                "```python\n"
                f"{finding.evidence}\n"
                "```"
            )

        sections.append(section)

    return "\n\n---\n\n".join(sections)


def build_annotations(
    findings: list[RiskFinding],
) -> list[dict]:
    """
    Convert Canary findings into GitHub Check annotations.

    These appear directly alongside affected lines in the PR diff.
    """

    annotation_levels = {
        Severity.HIGH: "failure",
        Severity.MEDIUM: "warning",
        Severity.LOW: "notice",
    }

    annotations: list[dict] = []

    for finding in findings:
        if finding.line is None:
            continue

        annotation = {
            "path": finding.filename,
            "start_line": finding.line,
            "end_line": finding.line,
            "annotation_level": annotation_levels[finding.severity],
            "title": f"Canary · {finding.category}",
            "message": finding.message,
        }

        if finding.evidence:
            annotation["raw_details"] = finding.evidence

        annotations.append(annotation)

    # GitHub accepts a maximum of 50 annotations
    # in a single Check Run API request.
    return annotations[:50]


async def create_canary_check(
    repository: str,
    head_sha: str,
    installation_id: int,
    findings: list[RiskFinding],
) -> None:
    """
    Publish Canary's analysis as a GitHub Check Run.

    Example:
        success -> no regression signals
        neutral -> low/medium findings
        failure -> at least one high-severity finding
    """

    github = GitHubClient()

    installation_token = await github.get_installation_token(
        installation_id
    )

    conclusion = determine_conclusion(findings)

    if conclusion == "success":
        title = "✅ No regression risks detected"

    elif conclusion == "failure":
        title = (
            f"❌ {len(findings)} potential "
            "regression risk(s) detected"
        )

    else:
        title = (
            f"⚠️ {len(findings)} potential "
            "regression risk(s) detected"
        )

    payload = {
        "name": "Canary",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title,
            "summary": build_check_summary(findings),
            "text": build_check_text(findings),
            "annotations": build_annotations(findings),
        },
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