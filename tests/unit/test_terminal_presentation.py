from io import StringIO

from rich.console import Console

from app.models import AnalysisResult, RiskFinding, Severity
from app.terminal.presentation import (
    build_terminal_bar,
    get_terminal_risk,
    render_analysis,
)


def make_finding(
    severity: Severity,
    *,
    line: int | None = 1,
    evidence: str | None = None,
) -> RiskFinding:
    return RiskFinding(
        category="PUBLIC_API_CHANGE",
        severity=severity,
        filename="auth.py",
        message="Function signature changed for `authenticate`.",
        line=line,
        evidence=evidence,
    )


def make_console() -> tuple[Console, StringIO]:
    output = StringIO()

    console = Console(
        file=output,
        width=100,
        color_system=None,
        force_terminal=False,
    )

    return console, output


def test_terminal_risk_is_all_clear_without_findings():
    result = AnalysisResult()

    icon, label, style = get_terminal_risk(result)

    assert icon == "🟢"
    assert label == "ALL CLEAR"
    assert style == "bold green"


def test_terminal_risk_uses_highest_severity():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.LOW),
            make_finding(Severity.HIGH),
            make_finding(Severity.MEDIUM),
        ]
    )

    icon, label, style = get_terminal_risk(result)

    assert icon == "🔴"
    assert label == "HIGH RISK"
    assert style == "bold red"


def test_terminal_bar_handles_empty_result():
    assert build_terminal_bar(
        count=0,
        total=0,
        width=4,
    ) == "░░░░"


def test_terminal_bar_represents_proportion():
    assert build_terminal_bar(
        count=1,
        total=2,
        width=4,
    ) == "██░░"


def test_render_high_risk_analysis():
    console, output = make_console()

    result = AnalysisResult(
        findings=[
            make_finding(
                Severity.HIGH,
                evidence=(
                    "def authenticate(token): → "
                    "def authenticate(token, strict=False):"
                ),
            )
        ],
        files_analyzed=1,
        python_files_analyzed=1,
        functions_inspected=1,
        changed_lines=2,
        additions=1,
        deletions=1,
    )

    render_analysis(
        console,
        repository="cybr-wisp/canary-testbed",
        pull_number=1,
        result=result,
    )

    text = output.getvalue()

    assert "CANARY" in text
    assert "cybr-wisp/canary-testbed" in text
    assert "HIGH RISK" in text
    assert "PUBLIC_API_CHANGE" in text
    assert "auth.py:1" in text
    assert "- def authenticate(token):" in text
    assert "+ def authenticate(token, strict=False):" in text
    assert "Review required before merge" in text


def test_render_safe_analysis():
    console, output = make_console()

    result = AnalysisResult(
        files_analyzed=3,
        python_files_analyzed=2,
        functions_inspected=8,
        changed_lines=31,
    )

    render_analysis(
        console,
        repository="example/project",
        pull_number=12,
        result=result,
    )

    text = output.getvalue()

    assert "ALL CLEAR" in text
    assert "No deterministic behavioral regression signals detected" in text
    assert "No Canary regression signals require review" in text
    assert "example/project" in text
    assert "#12" in text