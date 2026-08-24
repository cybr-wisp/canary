from app.models import (
    AnalysisResult,
    RiskFinding,
    Severity,
    ValidatedCompatibilityImpact,
)


SEVERITY_ICONS = {
    Severity.HIGH: "🔴",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
}

ANNOTATION_LEVELS = {
    Severity.HIGH: "failure",
    Severity.MEDIUM: "warning",
    Severity.LOW: "notice",
}


def pluralize(
    count: int,
    singular: str,
    plural: str | None = None,
) -> str:
    """Return the correct singular or plural word."""

    if count == 1:
        return singular

    return plural or f"{singular}s"


def get_overall_risk(
    result: AnalysisResult,
) -> tuple[str, str]:
    """
    Return the icon and label for the overall PR risk level.
    """

    if result.high_risk_count:
        return "🔴", "HIGH RISK"

    if result.medium_risk_count:
        return "🟡", "MEDIUM RISK"

    if result.low_risk_count:
        return "🔵", "LOW RISK"

    return "🟢", "ALL CLEAR"


def build_risk_bar(
    count: int,
    total: int,
    width: int = 10,
) -> str:
    """
    Create a small text-based bar for GitHub Markdown.

    Example:

        █████░░░░░
    """

    if total <= 0:
        return "░" * width

    filled = round(
        (count / total) * width
    )

    filled = max(
        0,
        min(width, filled),
    )

    return (
        "█" * filled
        + "░" * (width - filled)
    )


def _semantic_impact_counts(
    result: AnalysisResult,
) -> tuple[int, int, int, int]:
    """
    Return:

        (
            affected_calls,
            breaking_calls,
            compatible_calls,
            unknown_calls,
        )
    """

    affected_calls = 0
    breaking_calls = 0
    unknown_calls = 0

    for validated in result.validated_impacts:
        affected_calls += len(
            validated.assessments
        )

        breaking_calls += (
            validated.breaking_call_count
        )

        unknown_calls += len(
            validated.unknown_call_sites
        )

    compatible_calls = (
        affected_calls
        - breaking_calls
        - unknown_calls
    )

    return (
        affected_calls,
        breaking_calls,
        compatible_calls,
        unknown_calls,
    )


def build_check_title(
    result: AnalysisResult,
) -> str:
    """
    Build the short title GitHub displays beside the Canary check.
    """

    if result.finding_count == 0:
        return (
            "✅ All clear — "
            "no regression risks detected"
        )

    risk_word = pluralize(
        result.finding_count,
        "risk",
    )

    if result.has_high_risk:
        return (
            f"❌ {result.finding_count} potential "
            f"regression {risk_word} detected"
        )

    return (
        f"⚠️ {result.finding_count} potential "
        f"regression {risk_word} detected"
    )


def build_check_summary(
    result: AnalysisResult,
) -> str:
    """
    Build Canary's top-level GitHub Check summary.
    """

    risk_icon, risk_label = (
        get_overall_risk(result)
    )

    if result.finding_count == 0:
        return (
            "## 🐤 CANARY\n\n"
            "### ✅ All clear\n\n"
            "No deterministic behavioral regression signals "
            "were detected.\n\n"
            "### Analysis\n\n"
            "| Metric | Result |\n"
            "| --- | ---: |\n"
            f"| Files analyzed | "
            f"**{result.files_analyzed}** |\n"
            f"| Python files | "
            f"**{result.python_files_analyzed}** |\n"
            f"| Functions inspected | "
            f"**{result.functions_inspected}** |\n"
            f"| Lines changed | "
            f"**{result.changed_lines}** |\n"
            f"| Additions | "
            f"**+{result.additions}** |\n"
            f"| Deletions | "
            f"**-{result.deletions}** |\n\n"
            "---\n\n"
            "✅ **Merge recommendation:** "
            "No Canary regression signals require review."
        )

    total = result.finding_count

    signal_word = pluralize(
        result.finding_count,
        "signal",
    )

    file_word = pluralize(
        result.files_analyzed,
        "file",
    )

    high_bar = build_risk_bar(
        result.high_risk_count,
        total,
    )

    medium_bar = build_risk_bar(
        result.medium_risk_count,
        total,
    )

    low_bar = build_risk_bar(
        result.low_risk_count,
        total,
    )

    recommendation = (
        "❌ **Review required before merge.**"
        if result.has_high_risk
        else "⚠️ **Review recommended before merge.**"
    )

    summary = (
        "## 🐤 CANARY\n\n"
        f"### {risk_icon} {risk_label}\n\n"
        f"**{result.finding_count} regression "
        f"{signal_word} detected** "
        f"across **{result.files_analyzed} "
        f"{file_word}**.\n\n"
        "### Risk summary\n\n"
        "| Severity | Signal | Findings |\n"
        "| --- | --- | ---: |\n"
        f"| 🔴 High | `{high_bar}` | "
        f"**{result.high_risk_count}** |\n"
        f"| 🟡 Medium | `{medium_bar}` | "
        f"**{result.medium_risk_count}** |\n"
        f"| 🔵 Low | `{low_bar}` | "
        f"**{result.low_risk_count}** |\n\n"
    )

    if result.validated_impacts:
        (
            affected_calls,
            breaking_calls,
            compatible_calls,
            unknown_calls,
        ) = _semantic_impact_counts(
            result
        )

        summary += (
            "### Repository impact\n\n"
            "| Call-site status | Result |\n"
            "| --- | ---: |\n"
            f"| Call sites analyzed | "
            f"**{affected_calls}** |\n"
            f"| Confirmed breaking | "
            f"**{breaking_calls}** |\n"
            f"| Already compatible | "
            f"**{compatible_calls}** |\n"
            f"| Requires review | "
            f"**{unknown_calls}** |\n\n"
        )

    summary += (
        "### Analysis\n\n"
        "| Metric | Result |\n"
        "| --- | ---: |\n"
        f"| Files analyzed | "
        f"**{result.files_analyzed}** |\n"
        f"| Python files | "
        f"**{result.python_files_analyzed}** |\n"
        f"| Functions inspected | "
        f"**{result.functions_inspected}** |\n"
        f"| Lines changed | "
        f"**{result.changed_lines}** |\n"
        f"| Additions | "
        f"**+{result.additions}** |\n"
        f"| Deletions | "
        f"**-{result.deletions}** |\n\n"
        "---\n\n"
        f"{recommendation}"
    )

    return summary


def _format_evidence(
    evidence: str,
) -> str:
    """
    Make Canary's old → new evidence easier to read.

    Existing regression rules currently emit evidence such as:

        def authenticate(token) →
        def authenticate(token, strict=False)
    """

    if " → " not in evidence:
        return (
            "```text\n"
            f"{evidence}\n"
            "```"
        )

    old_value, new_value = (
        evidence.split(
            " → ",
            maxsplit=1,
        )
    )

    return (
        "```diff\n"
        f"- {old_value}\n"
        f"+ {new_value}\n"
        "```"
    )


def build_finding_section(
    finding: RiskFinding,
    index: int,
) -> str:
    """
    Render one Canary finding as GitHub Markdown.
    """

    icon = SEVERITY_ICONS[
        finding.severity
    ]

    location = (
        f"`{finding.filename}`"
    )

    if finding.line is not None:
        location += (
            f" · line `{finding.line}`"
        )

    section = (
        f"### {icon} "
        f"{finding.severity.value.upper()} "
        f"· {finding.category}\n\n"
        f"**Location:** {location}\n\n"
        f"{finding.message}"
    )

    if finding.evidence:
        section += (
            "\n\n"
            "<details>\n"
            f"<summary><strong>"
            f"View technical evidence "
            f"{index}"
            f"</strong></summary>\n\n"
            f"{_format_evidence(finding.evidence)}\n"
            "</details>"
        )

    return section


def _find_validated_impact(
    result: AnalysisResult,
    finding: RiskFinding,
) -> ValidatedCompatibilityImpact | None:
    """
    Find the validated repository impact associated with a finding.
    """

    for validated in result.validated_impacts:
        impact_finding = (
            validated.impact.finding
        )

        if (
            impact_finding is finding
            or impact_finding == finding
        ):
            return validated

    return None


def build_semantic_impact_section(
    validated: ValidatedCompatibilityImpact,
) -> str:
    """
    Render repository-wide call-site impact for one semantic finding.
    """

    assessments = (
        validated.assessments
    )

    if not assessments:
        return (
            "#### Repository impact\n\n"
            "No repository call sites were found "
            "for this changed symbol."
        )

    breaking_count = (
        validated.breaking_call_count
    )

    unknown_count = len(
        validated.unknown_call_sites
    )

    compatible_count = (
        len(assessments)
        - breaking_count
        - unknown_count
    )

    call_word = pluralize(
        len(assessments),
        "call site",
    )

    section = (
        "#### Repository impact\n\n"
        f"Canary found **{len(assessments)} "
        f"{call_word}** for this API.\n\n"
        "| Status | Calls |\n"
        "| --- | ---: |\n"
        f"| ❌ Confirmed breaking | "
        f"**{breaking_count}** |\n"
        f"| ✅ Compatible | "
        f"**{compatible_count}** |\n"
        f"| ⚠️ Requires review | "
        f"**{unknown_count}** |"
    )

    if validated.breaking_call_sites:
        section += (
            "\n\n"
            "**Confirmed breakages**\n\n"
        )

        for assessment in assessments:
            if (
                assessment.call_site
                not in validated.breaking_call_sites
            ):
                continue

            call_site = (
                assessment.call_site
            )

            section += (
                f"- `{call_site.filename}:"
                f"{call_site.line}`"
            )

            if assessment.reason:
                section += (
                    f" — {assessment.reason}"
                )

            section += "\n"

    if validated.unknown_call_sites:
        section += (
            "\n"
            "**Requires manual review**\n\n"
        )

        for assessment in assessments:
            if (
                assessment.call_site
                not in validated.unknown_call_sites
            ):
                continue

            call_site = (
                assessment.call_site
            )

            section += (
                f"- `{call_site.filename}:"
                f"{call_site.line}`"
            )

            if assessment.reason:
                section += (
                    f" — {assessment.reason}"
                )

            section += "\n"

    return section.rstrip()


def build_check_text(
    result: AnalysisResult,
) -> str:
    """
    Build the detailed findings section of the GitHub Check.
    """

    if not result.findings:
        return (
            "### What Canary inspected\n\n"
            "Canary analyzed the pull-request changes and "
            "applied its deterministic regression rules.\n\n"
            "No findings were produced."
        )

    sections: list[str] = []

    for index, finding in enumerate(
        result.findings,
        start=1,
    ):
        section = build_finding_section(
            finding=finding,
            index=index,
        )

        validated = (
            _find_validated_impact(
                result,
                finding,
            )
        )

        if validated is not None:
            section += (
                "\n\n"
                + build_semantic_impact_section(
                    validated
                )
            )

        sections.append(
            section
        )

    return (
        "## Detected regression signals\n\n"
        + "\n\n---\n\n".join(
            sections
        )
        + "\n\n---\n\n"
        "### About this result\n\n"
        "Canary reports deterministic signals from "
        "the code change and, when possible, validates "
        "their impact against repository call sites. "
        "A finding identifies a change that deserves "
        "review; it does not automatically mean the "
        "change is incorrect."
    )


def build_annotations(
    result: AnalysisResult,
) -> list[dict]:
    """
    Convert Canary findings into GitHub Check annotations.

    GitHub displays these directly beside affected lines in
    the pull-request diff.
    """

    annotations: list[dict] = []

    for finding in result.findings:
        if finding.line is None:
            continue

        annotation = {
            "path": finding.filename,
            "start_line": finding.line,
            "end_line": finding.line,
            "annotation_level": (
                ANNOTATION_LEVELS[
                    finding.severity
                ]
            ),
            "title": (
                "Canary · "
                f"{finding.severity.value.upper()} · "
                f"{finding.category}"
            ),
            "message": finding.message,
        }

        if finding.evidence:
            annotation[
                "raw_details"
            ] = finding.evidence

        annotations.append(
            annotation
        )

    # GitHub Check Runs accept up to 50 annotations
    # in one request.
    return annotations[:50]


def build_check_output(
    result: AnalysisResult,
) -> dict:
    """
    Build the complete GitHub Check output object.

    Keeping this here means checks.py only needs to worry about
    authentication and sending the HTTP request.
    """

    return {
        "title": build_check_title(
            result
        ),
        "summary": build_check_summary(
            result
        ),
        "text": build_check_text(
            result
        ),
        "annotations": build_annotations(
            result
        ),
    }