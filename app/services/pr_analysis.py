from __future__ import annotations

import re

from app.analysis.analyzer import (
    analyze_file,
)
from app.analysis.ast_analyzer import (
    analyze_python_source,
)
from app.analysis.call_validation import (
    validate_compatibility_impacts,
)
from app.analysis.compatibility import (
    compare_modules,
)
from app.analysis.diff_parser import (
    parse_patch,
)
from app.analysis.impact import (
    analyze_compatibility_impact,
)
from app.analysis.repository_analyzer import (
    analyze_repository_sources,
)
from app.github.client import GitHubClient
from app.models import (
    AnalysisResult,
    ChangedFile,
    ModuleAnalysis,
)


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

    if not (
        changed_file.filename.endswith(".py")
        or (
            changed_file.previous_filename
            and changed_file.previous_filename.endswith(
                ".py"
            )
        )
    ):
        return 0

    function_names: set[str] = set()

    for line in parse_patch(
        changed_file
    ):
        match = FUNCTION_PATTERN.match(
            line.content
        )

        if match:
            function_names.add(
                match.group("name")
            )

    return len(
        function_names
    )


def _is_python_change(
    changed_file: ChangedFile,
) -> bool:
    if changed_file.filename.endswith(
        ".py"
    ):
        return True

    previous = (
        changed_file.previous_filename
    )

    return bool(
        previous
        and previous.endswith(".py")
    )


def _module_from_source(
    source: str | None,
    *,
    filename: str,
) -> ModuleAnalysis:
    """
    Convert a source snapshot into ModuleAnalysis.

    Missing source represents an empty side of the comparison:

    - added file:
        no BASE source

    - deleted file:
        no HEAD source
    """

    if source is None:
        return ModuleAnalysis(
            filename=filename
        )

    return analyze_python_source(
        source,
        filename,
    )


async def analyze_pull_request(
    repository: str,
    pull_number: int,
    installation_id: int,
) -> AnalysisResult:
    """
    Analyze a pull request using Canary v2.

    Pipeline:

        PR metadata
            ↓
        BASE + HEAD refs
            ↓
        changed files
            ↓
        HEAD repository snapshot
            ↓
        AST analysis
            ↓
        compatibility detection
            ↓
        cross-file call-site resolution
            ↓
        impact analysis
            ↓
        argument-aware validation

    If a particular changed Python file cannot be parsed
    semantically, Canary falls back to its v1 diff analyzer for
    that file rather than dropping analysis entirely.
    """

    client = GitHubClient()

    changed_files = (
        await client.get_pull_request_files(
            repository=repository,
            pull_number=pull_number,
            installation_id=installation_id,
        )
    )

    base_sha, head_sha = (
        await client.get_pull_request_refs(
            repository=repository,
            pull_number=pull_number,
            installation_id=installation_id,
        )
    )

    head_sources = (
        await client.get_repository_python_sources(
            repository=repository,
            ref=head_sha,
            installation_id=installation_id,
        )
    )

    repository_analysis = (
        analyze_repository_sources(
            head_sources
        )
    )

    result = AnalysisResult(
        files_analyzed=len(
            changed_files
        ),
        python_files_analyzed=sum(
            _is_python_change(
                changed_file
            )
            for changed_file in changed_files
        ),
        additions=sum(
            changed_file.additions
            for changed_file
            in changed_files
        ),
        deletions=sum(
            changed_file.deletions
            for changed_file
            in changed_files
        ),
    )

    result.changed_lines = (
        result.additions
        + result.deletions
    )

    for changed_file in changed_files:
        result.functions_inspected += (
            _count_functions_in_patch(
                changed_file
            )
        )

        if not _is_python_change(
            changed_file
        ):
            continue

        before_filename = (
            changed_file.previous_filename
            or changed_file.filename
        )

        after_filename = (
            changed_file.filename
        )

        before_source = (
            await client.get_python_file_source(
                repository=repository,
                path=before_filename,
                ref=base_sha,
                installation_id=installation_id,
            )
        )

        after_source = head_sources.get(
            after_filename
        )

        try:
            before_module = (
                _module_from_source(
                    before_source,
                    filename=before_filename,
                )
            )

            after_module = (
                _module_from_source(
                    after_source,
                    filename=after_filename,
                )
            )

        except ValueError:
            # Syntax error or unsupported Python source.
            #
            # Preserve Canary's existing v1 behavior as a
            # per-file fallback.
            result.findings.extend(
                analyze_file(
                    changed_file
                )
            )

            continue

        semantic_findings = (
            compare_modules(
                before_module,
                after_module,
            )
        )

        result.findings.extend(
            semantic_findings
        )

        if not semantic_findings:
            continue

        impacts = (
            analyze_compatibility_impact(
                semantic_findings,
                before=before_module,
                after=after_module,
                repository=repository_analysis,
            )
        )

        validated_impacts = (
            validate_compatibility_impacts(
                impacts,
                before=before_module,
                after=after_module,
            )
        )

        result.validated_impacts.extend(
            validated_impacts
        )

    return result