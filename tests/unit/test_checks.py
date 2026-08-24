from app.github.checks import determine_conclusion
from app.models import AnalysisResult, RiskFinding, Severity


def make_finding(severity: Severity) -> RiskFinding:
    return RiskFinding(
        category="TEST_FINDING",
        severity=severity,
        filename="example.py",
        message="Test regression signal.",
        line=1,
    )


def test_no_findings_returns_success():
    result = AnalysisResult()

    assert determine_conclusion(result) == "success"


def test_low_risk_returns_neutral():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.LOW),
        ]
    )

    assert determine_conclusion(result) == "neutral"


def test_medium_risk_returns_neutral():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.MEDIUM),
        ]
    )

    assert determine_conclusion(result) == "neutral"


def test_high_risk_returns_failure():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
        ]
    )

    assert determine_conclusion(result) == "failure"


def test_high_risk_overrides_lower_severities():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.LOW),
            make_finding(Severity.MEDIUM),
            make_finding(Severity.HIGH),
        ]
    )

    assert determine_conclusion(result) == "failure"


def test_multiple_non_high_findings_remain_neutral():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.LOW),
            make_finding(Severity.MEDIUM),
            make_finding(Severity.LOW),
        ]
    )

    assert determine_conclusion(result) == "neutral"