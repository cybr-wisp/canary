from app.github.presentation import (
    build_annotations,
    build_check_output,
    build_check_summary,
    build_check_text,
    build_check_title,
    build_risk_bar,
    get_overall_risk,
)
from app.models import (
    AnalysisResult,
    CallImpactStatus,
    CallSite,
    CallSiteAssessment,
    CompatibilityImpact,
    RiskFinding,
    Severity,
    ValidatedCompatibilityImpact,
)


def make_finding(
    severity: Severity,
    *,
    category: str = "PUBLIC_API_CHANGE",
    filename: str = "auth.py",
    message: str = "Function signature changed.",
    line: int | None = 10,
    evidence: str | None = None,
) -> RiskFinding:
    return RiskFinding(
        category=category,
        severity=severity,
        filename=filename,
        message=message,
        line=line,
        evidence=evidence,
    )


def test_overall_risk_is_all_clear_without_findings():
    result = AnalysisResult()

    icon, label = get_overall_risk(result)

    assert icon == "🟢"
    assert label == "ALL CLEAR"


def test_overall_risk_uses_highest_severity():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.LOW),
            make_finding(Severity.HIGH),
            make_finding(Severity.MEDIUM),
        ]
    )

    icon, label = get_overall_risk(result)

    assert icon == "🔴"
    assert label == "HIGH RISK"


def test_safe_check_title():
    result = AnalysisResult()

    title = build_check_title(result)

    assert title == "✅ All clear — no regression risks detected"


def test_high_risk_check_title():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
        ]
    )

    title = build_check_title(result)

    assert title.startswith("❌")
    assert "1 potential regression risk detected" in title


def test_safe_summary_contains_real_analysis_statistics():
    result = AnalysisResult(
        files_analyzed=3,
        python_files_analyzed=2,
        functions_inspected=7,
        changed_lines=14,
        additions=10,
        deletions=4,
    )

    summary = build_check_summary(result)

    assert "🐤 CANARY" in summary
    assert "All clear" in summary
    assert "Files analyzed | **3**" in summary
    assert "Python files | **2**" in summary
    assert "Functions inspected | **7**" in summary
    assert "Lines changed | **14**" in summary
    assert "Additions | **+10**" in summary
    assert "Deletions | **-4**" in summary


def test_high_risk_summary_contains_merge_recommendation():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
        ],
        files_analyzed=1,
        python_files_analyzed=1,
        functions_inspected=1,
    )

    summary = build_check_summary(result)

    assert "🔴 HIGH RISK" in summary
    assert "Review required before merge" in summary
    assert "1 regression signal detected" in summary


def test_check_text_formats_old_and_new_evidence_as_diff():
    result = AnalysisResult(
        findings=[
            make_finding(
                Severity.HIGH,
                evidence=(
                    "def authenticate(token) → "
                    "def authenticate(token, strict=False)"
                ),
            )
        ]
    )

    text = build_check_text(result)

    assert "```diff" in text
    assert "- def authenticate(token)" in text
    assert "+ def authenticate(token, strict=False)" in text
    assert "PUBLIC_API_CHANGE" in text
    assert "View technical evidence 1" in text
    assert "View technical evidence #1" not in text


def test_high_risk_finding_becomes_failure_annotation():
    result = AnalysisResult(
        findings=[
            make_finding(
                Severity.HIGH,
                line=21,
            )
        ]
    )

    annotations = build_annotations(result)

    assert len(annotations) == 1

    annotation = annotations[0]

    assert annotation["path"] == "auth.py"
    assert annotation["start_line"] == 21
    assert annotation["end_line"] == 21
    assert annotation["annotation_level"] == "failure"


def test_medium_and_low_findings_use_correct_annotation_levels():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.MEDIUM, line=5),
            make_finding(Severity.LOW, line=8),
        ]
    )

    annotations = build_annotations(result)

    assert annotations[0]["annotation_level"] == "warning"
    assert annotations[1]["annotation_level"] == "notice"


def test_finding_without_line_is_not_annotated():
    result = AnalysisResult(
        findings=[
            make_finding(
                Severity.HIGH,
                line=None,
            )
        ]
    )

    annotations = build_annotations(result)

    assert annotations == []


def test_annotations_are_limited_to_fifty():
    result = AnalysisResult(
        findings=[
            make_finding(
                Severity.HIGH,
                line=index + 1,
            )
            for index in range(75)
        ]
    )

    annotations = build_annotations(result)

    assert len(annotations) == 50


def test_risk_bar_handles_empty_result():
    assert build_risk_bar(
        count=0,
        total=0,
    ) == "░░░░░░░░░░"


def test_check_output_contains_all_github_fields():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
        ]
    )

    output = build_check_output(result)

    assert set(output.keys()) == {
        "title",
        "summary",
        "text",
        "annotations",
    }


def test_singular_finding_uses_singular_grammar():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
        ],
        files_analyzed=1,
    )

    title = build_check_title(result)
    summary = build_check_summary(result)

    assert "1 potential regression risk detected" in title
    assert "risk(s)" not in title
    assert "1 regression signal detected" in summary
    assert "across **1 file**" in summary
    assert "signal(s)" not in summary
    assert "file(s)" not in summary


def test_multiple_findings_use_plural_grammar():
    result = AnalysisResult(
        findings=[
            make_finding(Severity.HIGH),
            make_finding(Severity.MEDIUM),
            make_finding(Severity.LOW),
        ],
        files_analyzed=4,
    )

    title = build_check_title(result)
    summary = build_check_summary(result)

    assert "3 potential regression risks detected" in title
    assert "3 regression signals detected" in summary
    assert "across **4 files**" in summary
    assert "risk(s)" not in title
    assert "signal(s)" not in summary
    assert "file(s)" not in summary


def test_v2_check_renders_repository_impact_and_breaking_calls():
    finding = RiskFinding(
        category="REQUIRED_PARAMETER_ADDED",
        severity=Severity.HIGH,
        filename="app/users.py",
        message="Required parameter added: organization_id",
        line=1,
        symbol="create_user",
    )

    call_site = CallSite(
        filename="app/api.py",
        line=14,
        column=4,
        callee="create_user",
        resolved_callee="app.users.create_user",
        positional_argument_count=1,
    )

    impact = CompatibilityImpact(
        finding=finding,
        impact_severity=Severity.HIGH,
        call_sites=(call_site,),
    )

    assessment = CallSiteAssessment(
        call_site=call_site,
        status=CallImpactStatus.BREAKS,
        reason="missing required parameter 'organization_id'",
    )

    validated = ValidatedCompatibilityImpact(
        impact=impact,
        assessments=(assessment,),
    )

    result = AnalysisResult(
        findings=[finding],
        validated_impacts=[validated],
        files_analyzed=2,
        python_files_analyzed=2,
        functions_inspected=2,
    )

    summary = build_check_summary(result)
    text = build_check_text(result)

    assert "Repository impact" in summary
    assert "| Call sites analyzed | **1** |" in summary
    assert "| Confirmed breaking | **1** |" in summary

    assert "Repository impact" in text
    assert "Confirmed breakages" in text
    assert "`app/api.py:14`" in text
    assert "missing required parameter 'organization_id'" in text