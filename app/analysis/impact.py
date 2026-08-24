
from __future__ import annotations

from app.analysis.repository_analyzer import (
    find_call_sites,
)
from app.models import (
    CompatibilityImpact,
    FunctionInfo,
    ModuleAnalysis,
    RepositoryAnalysis,
    RiskFinding,
    Severity,
)


def _find_affected_function(
    finding: RiskFinding,
    *,
    before: ModuleAnalysis,
    after: ModuleAnalysis,
) -> FunctionInfo | None:
    """
    Resolve a semantic compatibility finding back to the function
    that caused it.

    Most changed APIs exist in the new module.

    Removed APIs only exist in the old module, so Canary falls
    back to the before snapshot.
    """

    if finding.symbol is None:
        return None

    function = after.functions.get(
        finding.symbol
    )

    if function is not None:
        return function

    return before.functions.get(
        finding.symbol
    )


def _calculate_impact_severity(
    finding: RiskFinding,
    *,
    affected_call_count: int,
) -> Severity:
    """
    Combine semantic severity with repository blast radius.

    Rules:

    - Public/high-risk compatibility breaks remain HIGH even when
      Canary cannot find an internal call site because external
      consumers may still depend on the API.

    - A medium-risk change becomes HIGH when it affects at least
      three known call sites.

    - Any medium-risk change remains at least MEDIUM.

    - A lower-risk change with known usage becomes MEDIUM.

    - Otherwise the impact is LOW.
    """

    if finding.severity == Severity.HIGH:
        return Severity.HIGH

    if affected_call_count >= 3:
        return Severity.HIGH

    if finding.severity == Severity.MEDIUM:
        return Severity.MEDIUM

    if affected_call_count > 0:
        return Severity.MEDIUM

    return Severity.LOW


def analyze_compatibility_impact(
    findings: list[RiskFinding],
    *,
    before: ModuleAnalysis,
    after: ModuleAnalysis,
    repository: RepositoryAnalysis,
) -> list[CompatibilityImpact]:
    """
    Connect compatibility findings to repository call sites.

    `repository` should normally represent the PR's HEAD snapshot.

    This allows Canary to answer:

        What changed?
        Which symbol changed?
        Where is that symbol still used?
        How large is the likely blast radius?

    Example:

        REQUIRED_PARAMETER_ADDED
            ↓
        app.users.create_user
            ↓
        3 matching call sites
            ↓
        HIGH impact
    """

    impacts: list[CompatibilityImpact] = []

    for finding in findings:
        function = _find_affected_function(
            finding,
            before=before,
            after=after,
        )

        if function is None:
            call_sites = ()

        else:
            matched_calls = find_call_sites(
                repository,
                defining_filename=finding.filename,
                function=function,
            )

            call_sites = tuple(
                matched_calls
            )

        severity = _calculate_impact_severity(
            finding,
            affected_call_count=len(
                call_sites
            ),
        )

        impacts.append(
            CompatibilityImpact(
                finding=finding,
                impact_severity=severity,
                call_sites=call_sites,
            )
        )

    return impacts