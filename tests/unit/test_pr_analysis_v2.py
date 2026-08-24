from unittest.mock import (
    AsyncMock,
    patch,
)

import pytest

from app.models import (
    CallImpactStatus,
    ChangedFile,
)
from app.services.pr_analysis import (
    analyze_pull_request,
)


@pytest.mark.asyncio
async def test_real_pr_pipeline_detects_breaking_call():
    before_source = """
def create_user(name: str):
    pass
"""

    after_source = """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""

    api_source = """
from app.users import create_user

def signup():
    create_user("Marie")
"""

    changed_file = ChangedFile(
        filename="app/users.py",
        patch=(
            "@@ -1 +1,4 @@\n"
            "-def create_user(name: str):\n"
            "+def create_user(\n"
            "+    name: str,\n"
            "+    organization_id: int,\n"
            "+):\n"
        ),
        additions=4,
        deletions=1,
        status="modified",
    )

    with patch(
        "app.services.pr_analysis.GitHubClient"
    ) as client_class:
        github = client_class.return_value

        github.get_pull_request_files = (
            AsyncMock(
                return_value=[
                    changed_file
                ]
            )
        )

        github.get_pull_request_refs = (
            AsyncMock(
                return_value=(
                    "base123",
                    "head456",
                )
            )
        )

        github.get_repository_python_sources = (
            AsyncMock(
                return_value={
                    "app/users.py": (
                        after_source
                    ),
                    "app/api.py": (
                        api_source
                    ),
                }
            )
        )

        github.get_python_file_source = (
            AsyncMock(
                return_value=(
                    before_source
                )
            )
        )

        result = await analyze_pull_request(
            repository="cybr-wisp/test",
            pull_number=1,
            installation_id=123,
        )

    categories = {
        finding.category
        for finding in result.findings
    }

    assert (
        "REQUIRED_PARAMETER_ADDED"
        in categories
    )

    assert len(
        result.validated_impacts
    ) == 1

    validated = (
        result.validated_impacts[0]
    )

    assert (
        validated.breaking_call_count
        == 1
    )

    assert (
        validated.breaking_call_sites[
            0
        ].filename
        == "app/api.py"
    )

    assert (
        validated.assessments[
            0
        ].status
        == CallImpactStatus.BREAKS
    )