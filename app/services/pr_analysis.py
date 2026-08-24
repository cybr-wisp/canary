import re

from app.analysis.analyzer import analyze_file
from app.analysis.diff_parser import parse_patch
from app.github.client import GitHubClient
from app.models import AnalysisResult, ChangedFile


FUNCTION_PATTERN = re.compile(
    r"^\s*(?:async\s+)?def\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\("
)


def _count_functions_in_patch(
    changed_file: ChangedFile,
) -> int:
    """
    Count unique Python functions visible in a changed file's diff.

    A function may appear once as a removed signature and once as an
    added signature, so names are deduplicated before counting.
    """

    if not changed_file.filename.endswith(".py"):
        return 0

    function_names: set[str] = set()

    for line in parse_patch(changed_file):
        match = FUNCTION_PATTERN.match(line.content)

        if match:
            function_names.add(match.group("name"))

    return len(function_names)


async def analyze_pull_request(
    repository: str,
    pull_number: int,
    installation_id: int,
) -> AnalysisResult:
    """
    Fetch and analyze every changed file in a pull request.

    Returns both regression findings and aggregate statistics used
    by Canary's GitHub and terminal interfaces.
    """

    client = GitHubClient()

    changed_files = await client.get_pull_request_files(
        repository=repository,
        pull_number=pull_number,
        installation_id=installation_id,
    )

    result = AnalysisResult(
        files_analyzed=len(changed_files),
        python_files_analyzed=sum(
            changed_file.filename.endswith(".py")
            for changed_file in changed_files
        ),
        additions=sum(
            changed_file.additions
            for changed_file in changed_files
        ),
        deletions=sum(
            changed_file.deletions
            for changed_file in changed_files
        ),
    )

    result.changed_lines = (
        result.additions
        + result.deletions
    )

    for changed_file in changed_files:
        result.functions_inspected += _count_functions_in_patch(
            changed_file
        )

        result.findings.extend(
            analyze_file(changed_file)
        )

    return result