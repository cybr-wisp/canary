from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.models import (
    AnalysisResult,
    RiskFinding,
    Severity,
    ValidatedCompatibilityImpact,
)


SEVERITY_STYLES = {
    Severity.HIGH: ("🔴", "bold red"),
    Severity.MEDIUM: ("🟡", "bold yellow"),
    Severity.LOW: ("🔵", "bold blue"),
}


def get_terminal_risk(
    result: AnalysisResult,
) -> tuple[str, str, str]:
    """Return icon, label, and Rich style for overall risk."""

    if result.high_risk_count:
        return "🔴", "HIGH RISK", "bold red"

    if result.medium_risk_count:
        return "🟡", "MEDIUM RISK", "bold yellow"

    if result.low_risk_count:
        return "🔵", "LOW RISK", "bold blue"

    return "🟢", "ALL CLEAR", "bold green"


def build_terminal_bar(
    count: int,
    total: int,
    width: int = 16,
) -> str:
    """Build a fixed-width terminal risk bar."""

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


def build_header() -> Panel:
    """Build Canary's terminal header."""

    title = Text()

    title.append(
        "🐤 CANARY\n",
        style="bold",
    )

    title.append(
        "Behavioral Regression Analysis",
        style="dim",
    )

    return Panel(
        title,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def build_metadata_table(
    repository: str,
    pull_number: int,
    result: AnalysisResult,
) -> Table:
    """Build pull-request and analysis metadata."""

    table = Table(
        box=None,
        show_header=False,
        padding=(0, 2),
    )

    table.add_column(
        style="dim",
    )

    table.add_column()

    table.add_row(
        "Repository",
        repository,
    )

    table.add_row(
        "Pull Request",
        f"#{pull_number}",
    )

    table.add_row(
        "Files analyzed",
        str(result.files_analyzed),
    )

    table.add_row(
        "Python files",
        str(
            result.python_files_analyzed
        ),
    )

    table.add_row(
        "Functions",
        str(
            result.functions_inspected
        ),
    )

    table.add_row(
        "Changed lines",
        str(result.changed_lines),
    )

    return table


def build_risk_summary(
    result: AnalysisResult,
) -> Table:
    """Build the terminal severity summary."""

    total = result.finding_count

    table = Table(
        title="Risk summary",
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column()
    table.add_column()
    table.add_column(
        justify="right",
    )

    table.add_row(
        "🔴 High",
        build_terminal_bar(
            result.high_risk_count,
            total,
        ),
        str(
            result.high_risk_count
        ),
    )

    table.add_row(
        "🟡 Medium",
        build_terminal_bar(
            result.medium_risk_count,
            total,
        ),
        str(
            result.medium_risk_count
        ),
    )

    table.add_row(
        "🔵 Low",
        build_terminal_bar(
            result.low_risk_count,
            total,
        ),
        str(
            result.low_risk_count
        ),
    )

    return table


def _semantic_impact_counts(
    result: AnalysisResult,
) -> tuple[int, int, int, int]:
    """
    Return repository call-site totals:

        (
            analyzed,
            breaking,
            compatible,
            unknown,
        )
    """

    analyzed = 0
    breaking = 0
    unknown = 0

    for validated in result.validated_impacts:
        analyzed += len(
            validated.assessments
        )

        breaking += (
            validated.breaking_call_count
        )

        unknown += len(
            validated.unknown_call_sites
        )

    compatible = (
        analyzed
        - breaking
        - unknown
    )

    return (
        analyzed,
        breaking,
        compatible,
        unknown,
    )


def build_repository_impact_summary(
    result: AnalysisResult,
) -> Table:
    """
    Build repository-wide semantic impact statistics.
    """

    (
        analyzed,
        breaking,
        compatible,
        unknown,
    ) = _semantic_impact_counts(
        result
    )

    table = Table(
        title="Repository impact",
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column()
    table.add_column(
        justify="right",
    )

    table.add_row(
        "Call sites analyzed",
        str(analyzed),
    )

    table.add_row(
        "❌ Confirmed breaking",
        str(breaking),
    )

    table.add_row(
        "✅ Compatible",
        str(compatible),
    )

    table.add_row(
        "⚠️ Requires review",
        str(unknown),
    )

    return table


def _find_validated_impact(
    result: AnalysisResult,
    finding: RiskFinding,
) -> ValidatedCompatibilityImpact | None:
    """
    Find repository impact associated with a finding.
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


def _append_semantic_impact(
    content: Text,
    validated: ValidatedCompatibilityImpact,
) -> None:
    """
    Append repository call-site analysis to a finding.
    """

    assessments = (
        validated.assessments
    )

    content.append(
        "\n\nRepository impact",
        style="bold",
    )

    if not assessments:
        content.append(
            "\nNo repository call sites found.",
            style="dim",
        )
        return

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

    content.append(
        f"\n{len(assessments)} call site"
    )

    if len(assessments) != 1:
        content.append("s")

    content.append(" analyzed")

    content.append(
        f"\n❌ {breaking_count} confirmed breaking",
        style=(
            "bold red"
            if breaking_count
            else "dim"
        ),
    )

    content.append(
        f"\n✅ {compatible_count} compatible",
        style=(
            "green"
            if compatible_count
            else "dim"
        ),
    )

    content.append(
        f"\n⚠️ {unknown_count} require review",
        style=(
            "yellow"
            if unknown_count
            else "dim"
        ),
    )

    if validated.breaking_call_sites:
        content.append(
            "\n\nConfirmed breakages",
            style="bold red",
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

            content.append(
                "\n• ",
                style="red",
            )

            content.append(
                f"{call_site.filename}:"
                f"{call_site.line}",
                style="bold",
            )

            if assessment.reason:
                content.append(
                    f" — {assessment.reason}",
                    style="dim",
                )

    if validated.unknown_call_sites:
        content.append(
            "\n\nRequires manual review",
            style="bold yellow",
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

            content.append(
                "\n• ",
                style="yellow",
            )

            content.append(
                f"{call_site.filename}:"
                f"{call_site.line}",
                style="bold",
            )

            if assessment.reason:
                content.append(
                    f" — {assessment.reason}",
                    style="dim",
                )


def build_finding_panel(
    finding: RiskFinding,
    validated: ValidatedCompatibilityImpact | None = None,
) -> Panel:
    """Render one regression finding."""

    icon, style = (
        SEVERITY_STYLES[
            finding.severity
        ]
    )

    content = Text()

    location = finding.filename

    if finding.line is not None:
        location += (
            f":{finding.line}"
        )

    content.append(
        location,
        style="bold",
    )

    content.append("\n\n")

    content.append(
        finding.message
    )

    if finding.evidence:
        content.append("\n\n")

        if " → " in finding.evidence:
            (
                old_value,
                new_value,
            ) = finding.evidence.split(
                " → ",
                maxsplit=1,
            )

            content.append(
                "- ",
                style="red",
            )

            content.append(
                old_value,
                style="red",
            )

            content.append("\n")

            content.append(
                "+ ",
                style="green",
            )

            content.append(
                new_value,
                style="green",
            )

        else:
            content.append(
                finding.evidence,
                style="dim",
            )

    if validated is not None:
        _append_semantic_impact(
            content,
            validated,
        )

    return Panel(
        content,
        title=(
            f"{icon} "
            f"{finding.severity.value.upper()} "
            f"· {finding.category}"
        ),
        title_align="left",
        border_style=style,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def build_recommendation(
    result: AnalysisResult,
) -> Text:
    """Build Canary's final recommendation."""

    if result.has_high_risk:
        return Text(
            "❌ Review required before merge.",
            style="bold red",
        )

    if result.finding_count:
        return Text(
            "⚠️ Review recommended before merge.",
            style="bold yellow",
        )

    return Text(
        "✅ No Canary regression signals require review.",
        style="bold green",
    )


def render_analysis(
    console: Console,
    *,
    repository: str,
    pull_number: int,
    result: AnalysisResult,
) -> None:
    """Render a complete Canary terminal report."""

    console.print()

    console.print(
        build_header()
    )

    console.print()

    console.print(
        build_metadata_table(
            repository=repository,
            pull_number=pull_number,
            result=result,
        )
    )

    console.print()

    (
        risk_icon,
        risk_label,
        risk_style,
    ) = get_terminal_risk(
        result
    )

    console.print(
        Text(
            f"{risk_icon} {risk_label}",
            style=risk_style,
        )
    )

    console.print()

    if not result.findings:
        console.print(
            "No deterministic behavioral regression "
            "signals detected."
        )

        console.print()

        console.print(
            build_recommendation(
                result
            )
        )

        console.print()

        return

    finding_panels = []

    for finding in result.findings:
        validated = (
            _find_validated_impact(
                result,
                finding,
            )
        )

        finding_panels.append(
            build_finding_panel(
                finding,
                validated,
            )
        )

    console.print(
        Group(
            *finding_panels
        )
    )

    console.print()

    console.print(
        build_risk_summary(
            result
        )
    )

    if result.validated_impacts:
        console.print()

        console.print(
            build_repository_impact_summary(
                result
            )
        )

    console.print()

    console.print(
        build_recommendation(
            result
        )
    )

    console.print()