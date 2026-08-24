from __future__ import annotations

from app.models import (
    CallImpactStatus,
    CallSite,
    CallSiteAssessment,
    CompatibilityImpact,
    FunctionInfo,
    ModuleAnalysis,
    ParameterInfo,
    ValidatedCompatibilityImpact,
)


IGNORED_IMPLICIT_PARAMETERS = {
    "self",
    "cls",
}


def _external_parameters(
    function: FunctionInfo,
) -> tuple[ParameterInfo, ...]:
    return tuple(
        parameter
        for parameter in function.parameters
        if parameter.name
        not in IGNORED_IMPLICIT_PARAMETERS
    )


def _call_is_compatible(
    call: CallSite,
    function: FunctionInfo,
) -> bool | None:
    """
    Perform lightweight static argument binding.

    Returns:

        True
            call is compatible

        False
            call is definitely incompatible

        None
            Canary cannot prove compatibility because *args
            or **kwargs are involved
    """

    if (
        call.has_star_args
        or call.has_star_kwargs
    ):
        return None

    parameters = _external_parameters(
        function
    )

    parameter_map = {
        parameter.name: parameter
        for parameter in parameters
    }

    positional_parameters = [
        parameter
        for parameter in parameters
        if parameter.kind in {
            "positional_only",
            "positional_or_keyword",
        }
    ]

    has_var_positional = any(
        parameter.kind
        == "var_positional"
        for parameter in parameters
    )

    has_var_keyword = any(
        parameter.kind
        == "var_keyword"
        for parameter in parameters
    )

    if (
        call.positional_argument_count
        > len(positional_parameters)
        and not has_var_positional
    ):
        return False

    bound_by_position = {
        parameter.name
        for parameter in positional_parameters[
            : call.positional_argument_count
        ]
    }

    bound_by_keyword: set[str] = set()

    for name in call.keyword_arguments:
        parameter = parameter_map.get(
            name
        )

        if parameter is None:
            if not has_var_keyword:
                return False

            continue

        if (
            parameter.kind
            == "positional_only"
        ):
            return False

        if name in bound_by_position:
            return False

        bound_by_keyword.add(
            name
        )

    for parameter in parameters:
        if parameter.kind in {
            "var_positional",
            "var_keyword",
        }:
            continue

        if parameter.has_default:
            continue

        if (
            parameter.name
            in bound_by_position
        ):
            continue

        if (
            parameter.name
            in bound_by_keyword
        ):
            continue

        return False

    return True


def _positional_bindings(
    call: CallSite,
    function: FunctionInfo,
) -> tuple[str, ...] | None:
    """
    Determine which parameter names positional arguments bind to.
    """

    if call.has_star_args:
        return None

    parameters = [
        parameter
        for parameter in _external_parameters(
            function
        )
        if parameter.kind in {
            "positional_only",
            "positional_or_keyword",
        }
    ]

    if (
        call.positional_argument_count
        > len(parameters)
    ):
        return None

    return tuple(
        parameter.name
        for parameter in parameters[
            : call.positional_argument_count
        ]
    )


def _assess_parameter_change(
    call: CallSite,
    before: FunctionInfo,
    after: FunctionInfo,
) -> CallSiteAssessment:
    old_compatible = (
        _call_is_compatible(
            call,
            before,
        )
    )

    new_compatible = (
        _call_is_compatible(
            call,
            after,
        )
    )

    if (
        old_compatible is None
        or new_compatible is None
    ):
        return CallSiteAssessment(
            call_site=call,
            status=(
                CallImpactStatus.UNKNOWN
            ),
            reason=(
                "Call uses *args or **kwargs; "
                "compatibility cannot be proven."
            ),
        )

    if (
        old_compatible
        and not new_compatible
    ):
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.BREAKS,
            reason=(
                "Call was valid before the API "
                "change but is incompatible with "
                "the new signature."
            ),
        )

    return CallSiteAssessment(
        call_site=call,
        status=CallImpactStatus.UNAFFECTED,
        reason=(
            "Call remains compatible with the "
            "new signature."
        ),
    )


def _assess_reordering(
    call: CallSite,
    before: FunctionInfo,
    after: FunctionInfo,
) -> CallSiteAssessment:
    old_bindings = _positional_bindings(
        call,
        before,
    )

    new_bindings = _positional_bindings(
        call,
        after,
    )

    if (
        old_bindings is None
        or new_bindings is None
    ):
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.UNKNOWN,
            reason=(
                "Positional binding cannot be "
                "determined statically."
            ),
        )

    if old_bindings != new_bindings:
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.BREAKS,
            reason=(
                "Positional arguments now bind "
                "to different parameters."
            ),
        )

    return CallSiteAssessment(
        call_site=call,
        status=CallImpactStatus.UNAFFECTED,
        reason=(
            "This call does not depend on the "
            "changed positional order."
        ),
    )


def _assess_async_change(
    call: CallSite,
    before: FunctionInfo,
    after: FunctionInfo,
) -> CallSiteAssessment:
    # sync -> async
    if (
        not before.is_async
        and after.is_async
    ):
        if not call.is_awaited:
            return CallSiteAssessment(
                call_site=call,
                status=CallImpactStatus.BREAKS,
                reason=(
                    "Function became async but "
                    "this call is not awaited."
                ),
            )

        return CallSiteAssessment(
            call_site=call,
            status=(
                CallImpactStatus.UNAFFECTED
            ),
            reason=(
                "Call already awaits the async "
                "function."
            ),
        )

    # async -> sync
    if (
        before.is_async
        and not after.is_async
    ):
        if call.is_awaited:
            return CallSiteAssessment(
                call_site=call,
                status=CallImpactStatus.BREAKS,
                reason=(
                    "Function became synchronous "
                    "but this call still uses await."
                ),
            )

    return CallSiteAssessment(
        call_site=call,
        status=CallImpactStatus.UNAFFECTED,
        reason=(
            "Call matches the new async behavior."
        ),
    )


def assess_call_site(
    *,
    category: str,
    call: CallSite,
    before: FunctionInfo | None,
    after: FunctionInfo | None,
) -> CallSiteAssessment:
    """
    Determine whether one specific call site is actually affected
    by a semantic API change.
    """

    if category == "PUBLIC_API_REMOVED":
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.BREAKS,
            reason=(
                "The referenced public API "
                "no longer exists."
            ),
        )

    if (
        before is None
        or after is None
    ):
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.UNKNOWN,
            reason=(
                "Function signature could not "
                "be resolved."
            ),
        )

    if category == "PARAMETER_REORDERED":
        return _assess_reordering(
            call,
            before,
            after,
        )

    if category == "ASYNC_BEHAVIOR_CHANGED":
        return _assess_async_change(
            call,
            before,
            after,
        )

    if category == "RETURN_TYPE_CHANGED":
        return CallSiteAssessment(
            call_site=call,
            status=CallImpactStatus.UNKNOWN,
            reason=(
                "Return type changed; Canary "
                "cannot yet determine how the "
                "returned value is consumed."
            ),
        )

    if category in {
        "REQUIRED_PARAMETER_ADDED",
        "PARAMETER_REMOVED",
        "PARAMETER_DEFAULT_REMOVED",
    }:
        return _assess_parameter_change(
            call,
            before,
            after,
        )

    return CallSiteAssessment(
        call_site=call,
        status=CallImpactStatus.UNKNOWN,
        reason=(
            "No call-site validator exists for "
            f"{category}."
        ),
    )


def validate_compatibility_impacts(
    impacts: list[CompatibilityImpact],
    *,
    before: ModuleAnalysis,
    after: ModuleAnalysis,
) -> list[ValidatedCompatibilityImpact]:
    """
    Refine repository impact analysis using the actual arguments
    supplied at each call site.
    """

    validated: list[
        ValidatedCompatibilityImpact
    ] = []

    for impact in impacts:
        finding = impact.finding

        symbol = finding.symbol

        before_function = (
            before.functions.get(symbol)
            if symbol is not None
            else None
        )

        after_function = (
            after.functions.get(symbol)
            if symbol is not None
            else None
        )

        assessments = tuple(
            assess_call_site(
                category=finding.category,
                call=call,
                before=before_function,
                after=after_function,
            )
            for call in impact.call_sites
        )

        validated.append(
            ValidatedCompatibilityImpact(
                impact=impact,
                assessments=assessments,
            )
        )

    return validated