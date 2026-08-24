from __future__ import annotations

from app.models import (
    FunctionInfo,
    ModuleAnalysis,
    ParameterInfo,
    RiskFinding,
    Severity,
)


IGNORED_IMPLICIT_PARAMETERS = {
    "self",
    "cls",
}


def _severity_for_function(
    function: FunctionInfo,
) -> Severity:
    """
    Public API compatibility changes are higher risk than
    changes to private helpers.
    """

    if function.is_public:
        return Severity.HIGH

    return Severity.MEDIUM


def _parameter_map(
    function: FunctionInfo,
) -> dict[str, ParameterInfo]:
    """
    Index function parameters by name.

    `self` and `cls` are ignored because Canary cares about the
    external calling contract rather than Python's implicit
    method receiver.
    """

    return {
        parameter.name: parameter
        for parameter in function.parameters
        if parameter.name
        not in IGNORED_IMPLICIT_PARAMETERS
    }


def _parameter_order(
    function: FunctionInfo,
) -> list[str]:
    """
    Return externally meaningful parameters in declaration order.
    """

    return [
        parameter.name
        for parameter in function.parameters
        if parameter.name
        not in IGNORED_IMPLICIT_PARAMETERS
    ]


def _function_signature(
    function: FunctionInfo,
) -> str:
    """
    Render a compact external function signature for evidence.

    Implicit method receivers such as self and cls are omitted.
    """

    parameters = [
        parameter.name
        for parameter in function.parameters
        if parameter.name
        not in IGNORED_IMPLICIT_PARAMETERS
    ]

    return (
        f"{function.qualname}"
        f"({', '.join(parameters)})"
    )


def _required_parameter(
    parameter: ParameterInfo,
) -> bool:
    """
    Determine whether a parameter introduces a required argument.

    *args and **kwargs never require the caller to provide a value.
    """

    if parameter.kind in {
        "var_positional",
        "var_keyword",
    }:
        return False

    return not parameter.has_default


def _detect_removed_function(
    before: FunctionInfo,
    *,
    filename: str,
) -> RiskFinding | None:
    """
    Report removal of a public function or method.
    """

    if not before.is_public:
        return None

    return RiskFinding(
        category="PUBLIC_API_REMOVED",
        severity=Severity.HIGH,
        filename=filename,
        line=before.line,
        message=(
            f"Public API `{before.qualname}` was removed."
        ),
        evidence=before.qualname,
        symbol=before.qualname,
    )


def _detect_required_parameters_added(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> list[RiskFinding]:
    """
    Detect newly added required parameters.
    """

    before_parameters = _parameter_map(before)
    after_parameters = _parameter_map(after)

    findings: list[RiskFinding] = []

    for name, parameter in after_parameters.items():
        if name in before_parameters:
            continue

        if not _required_parameter(parameter):
            continue

        findings.append(
            RiskFinding(
                category="REQUIRED_PARAMETER_ADDED",
                severity=_severity_for_function(after),
                filename=filename,
                line=after.line,
                message=(
                    f"Required parameter `{name}` was added "
                    f"to `{after.qualname}`."
                ),
                evidence=(
                    f"{_function_signature(before)} → "
                    f"{_function_signature(after)}"
                ),
                symbol=after.qualname,
            )
        )

    return findings


def _detect_parameters_removed(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> list[RiskFinding]:
    """
    Detect parameters that existed before but no longer exist.
    """

    before_parameters = _parameter_map(before)
    after_parameters = _parameter_map(after)

    findings: list[RiskFinding] = []

    for name in before_parameters:
        if name in after_parameters:
            continue

        findings.append(
            RiskFinding(
                category="PARAMETER_REMOVED",
                severity=_severity_for_function(after),
                filename=filename,
                line=after.line,
                message=(
                    f"Parameter `{name}` was removed from "
                    f"`{after.qualname}`."
                ),
                evidence=name,
                symbol=after.qualname,
            )
        )

    return findings


def _detect_parameter_reordering(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> RiskFinding | None:
    """
    Detect changes to the relative ordering of existing parameters.

    Added or removed parameters alone do not count as reordering.
    Canary compares only parameters that exist in both versions.
    """

    before_order = _parameter_order(before)
    after_order = _parameter_order(after)

    shared = set(before_order) & set(after_order)

    old_shared_order = [
        name
        for name in before_order
        if name in shared
    ]

    new_shared_order = [
        name
        for name in after_order
        if name in shared
    ]

    if old_shared_order == new_shared_order:
        return None

    return RiskFinding(
        category="PARAMETER_REORDERED",
        severity=_severity_for_function(after),
        filename=filename,
        line=after.line,
        message=(
            f"Parameter order changed for "
            f"`{after.qualname}`."
        ),
        evidence=(
            f"{', '.join(old_shared_order)} "
            f"→ {', '.join(new_shared_order)}"
        ),
        symbol=after.qualname,
    )


def _detect_defaults_removed(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> list[RiskFinding]:
    """
    Detect parameters that previously had defaults but became
    required.
    """

    before_parameters = _parameter_map(before)
    after_parameters = _parameter_map(after)

    findings: list[RiskFinding] = []

    for name, old_parameter in before_parameters.items():
        new_parameter = after_parameters.get(name)

        if new_parameter is None:
            continue

        if not old_parameter.has_default:
            continue

        if new_parameter.has_default:
            continue

        findings.append(
            RiskFinding(
                category="PARAMETER_DEFAULT_REMOVED",
                severity=_severity_for_function(after),
                filename=filename,
                line=after.line,
                message=(
                    f"Default value was removed from "
                    f"parameter `{name}` in "
                    f"`{after.qualname}`."
                ),
                evidence=name,
                symbol=after.qualname,
            )
        )

    return findings


def _detect_return_annotation_change(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> RiskFinding | None:
    """
    Detect changes in an explicit return type annotation.
    """

    if (
        before.return_annotation
        == after.return_annotation
    ):
        return None

    return RiskFinding(
        category="RETURN_TYPE_CHANGED",
        severity=_severity_for_function(after),
        filename=filename,
        line=after.line,
        message=(
            f"Return annotation changed for "
            f"`{after.qualname}`."
        ),
        evidence=(
            f"{before.return_annotation or 'None'} "
            f"→ "
            f"{after.return_annotation or 'None'}"
        ),
        symbol=after.qualname,
    )


def _detect_async_change(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> RiskFinding | None:
    """
    Detect sync-to-async or async-to-sync API changes.
    """

    if before.is_async == after.is_async:
        return None

    before_kind = (
        "async"
        if before.is_async
        else "sync"
    )

    after_kind = (
        "async"
        if after.is_async
        else "sync"
    )

    return RiskFinding(
        category="ASYNC_BEHAVIOR_CHANGED",
        severity=_severity_for_function(after),
        filename=filename,
        line=after.line,
        message=(
            f"`{after.qualname}` changed from "
            f"{before_kind} to {after_kind}."
        ),
        evidence=(
            f"{before_kind} → {after_kind}"
        ),
        symbol=after.qualname,
    )


def compare_function(
    before: FunctionInfo,
    after: FunctionInfo,
    *,
    filename: str,
) -> list[RiskFinding]:
    """
    Compare two versions of the same Python function.

    Returns compatibility findings describing potentially breaking
    behavioral/API changes.
    """

    findings: list[RiskFinding] = []

    findings.extend(
        _detect_required_parameters_added(
            before,
            after,
            filename=filename,
        )
    )

    findings.extend(
        _detect_parameters_removed(
            before,
            after,
            filename=filename,
        )
    )

    reordered = _detect_parameter_reordering(
        before,
        after,
        filename=filename,
    )

    if reordered is not None:
        findings.append(reordered)

    findings.extend(
        _detect_defaults_removed(
            before,
            after,
            filename=filename,
        )
    )

    return_change = (
        _detect_return_annotation_change(
            before,
            after,
            filename=filename,
        )
    )

    if return_change is not None:
        findings.append(return_change)

    async_change = _detect_async_change(
        before,
        after,
        filename=filename,
    )

    if async_change is not None:
        findings.append(async_change)

    return findings


def compare_modules(
    before: ModuleAnalysis,
    after: ModuleAnalysis,
) -> list[RiskFinding]:
    """
    Compare two versions of a Python module.

    This is Canary v2's semantic compatibility engine.

    It detects:

    - removed public APIs
    - required parameters added
    - parameters removed
    - parameters reordered
    - parameter defaults removed
    - return annotation changes
    - sync/async behavior changes
    """

    findings: list[RiskFinding] = []

    before_functions = before.functions
    after_functions = after.functions

    for qualname, old_function in before_functions.items():
        new_function = after_functions.get(
            qualname
        )

        if new_function is None:
            removed = _detect_removed_function(
                old_function,
                filename=after.filename,
            )

            if removed is not None:
                findings.append(removed)

            continue

        findings.extend(
            compare_function(
                old_function,
                new_function,
                filename=after.filename,
            )
        )

    return findings