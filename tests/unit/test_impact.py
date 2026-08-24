
from app.analysis.ast_analyzer import (
    analyze_python_source,
)
from app.analysis.compatibility import (
    compare_modules,
)
from app.analysis.impact import (
    analyze_compatibility_impact,
)
from app.analysis.repository_analyzer import (
    analyze_repository_sources,
)
from app.models import (
    RiskFinding,
    Severity,
)


def build_impact(
    *,
    before_source: str,
    after_source: str,
    repository_sources: dict[str, str],
):
    before = analyze_python_source(
        before_source,
        "app/users.py",
    )

    after = analyze_python_source(
        after_source,
        "app/users.py",
    )

    findings = compare_modules(
        before,
        after,
    )

    repository = (
        analyze_repository_sources(
            repository_sources
        )
    )

    return analyze_compatibility_impact(
        findings,
        before=before,
        after=after,
        repository=repository,
    )


def test_connects_breaking_change_to_three_call_sites():
    before_source = """
def create_user(name: str):
    pass
"""

    after_source = """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""

    impacts = build_impact(
        before_source=before_source,
        after_source=after_source,
        repository_sources={
            "app/users.py": after_source,
            "app/api.py": """
from app.users import create_user

def signup():
    create_user("Marie")
""",
            "app/admin.py": """
from app.users import create_user

def create_admin():
    create_user("Admin")
""",
            "tests/test_users.py": """
from app.users import create_user

def test_create():
    create_user("Test")
""",
        },
    )

    impact = next(
        item
        for item in impacts
        if item.finding.category
        == "REQUIRED_PARAMETER_ADDED"
    )

    assert impact.affected_call_count == 3

    assert impact.impact_severity == (
        Severity.HIGH
    )

    assert {
        call.filename
        for call in impact.call_sites
    } == {
        "app/api.py",
        "app/admin.py",
        "tests/test_users.py",
    }


def test_removed_function_finds_remaining_calls():
    before_source = """
def create_user(name: str):
    pass
"""

    after_source = """
def other_function():
    pass
"""

    impacts = build_impact(
        before_source=before_source,
        after_source=after_source,
        repository_sources={
            "app/users.py": after_source,
            "app/api.py": """
from app.users import create_user

def signup():
    create_user("Marie")
""",
        },
    )

    impact = next(
        item
        for item in impacts
        if item.finding.category
        == "PUBLIC_API_REMOVED"
    )

    assert impact.affected_call_count == 1

    assert (
        impact.call_sites[0].filename
        == "app/api.py"
    )

    assert (
        impact.impact_severity
        == Severity.HIGH
    )


def test_unrelated_same_named_function_is_not_affected():
    before_source = """
def create_user(name: str):
    pass
"""

    after_source = """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""

    impacts = build_impact(
        before_source=before_source,
        after_source=after_source,
        repository_sources={
            "app/users.py": after_source,
            "other/users.py": """
def create_user(name: str):
    pass
""",
            "app/api.py": """
from other.users import create_user

def signup():
    create_user("Marie")
""",
        },
    )

    impact = next(
        item
        for item in impacts
        if item.finding.category
        == "REQUIRED_PARAMETER_ADDED"
    )

    assert impact.affected_call_count == 0


def test_high_risk_api_remains_high_without_internal_calls():
    before_source = """
def create_user(name: str):
    pass
"""

    after_source = """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""

    impacts = build_impact(
        before_source=before_source,
        after_source=after_source,
        repository_sources={
            "app/users.py": after_source,
        },
    )

    impact = next(
        item
        for item in impacts
        if item.finding.category
        == "REQUIRED_PARAMETER_ADDED"
    )

    assert impact.affected_call_count == 0

    assert (
        impact.impact_severity
        == Severity.HIGH
    )


def test_multiple_findings_share_call_site_impact():
    before_source = """
def create_user(
    name: str,
    active: bool = True,
) -> str:
    return name
"""

    after_source = """
async def create_user(
    name: str,
    active: bool,
) -> int:
    return 1
"""

    impacts = build_impact(
        before_source=before_source,
        after_source=after_source,
        repository_sources={
            "app/users.py": after_source,
            "app/api.py": """
from app.users import create_user

def signup():
    create_user("Marie")
""",
        },
    )

    categories = {
        impact.finding.category
        for impact in impacts
    }

    assert (
        "PARAMETER_DEFAULT_REMOVED"
        in categories
    )

    assert (
        "RETURN_TYPE_CHANGED"
        in categories
    )

    assert (
        "ASYNC_BEHAVIOR_CHANGED"
        in categories
    )

    for impact in impacts:
        assert (
            impact.affected_call_count
            == 1
        )


def test_finding_without_symbol_does_not_crash():
    before = analyze_python_source(
        """
def create_user(name: str):
    pass
""",
        "app/users.py",
    )

    after = analyze_python_source(
        """
def create_user(name: str):
    pass
""",
        "app/users.py",
    )

    repository = (
        analyze_repository_sources(
            {
                "app/users.py": """
def create_user(name: str):
    pass
"""
            }
        )
    )

    finding = RiskFinding(
        category="LEGACY_RULE",
        severity=Severity.MEDIUM,
        filename="app/users.py",
        message="Legacy v1 finding",
    )

    impacts = analyze_compatibility_impact(
        [finding],
        before=before,
        after=after,
        repository=repository,
    )

    assert len(impacts) == 1

    assert (
        impacts[0].affected_call_count
        == 0
    )

    assert (
        impacts[0].impact_severity
        == Severity.MEDIUM
    )