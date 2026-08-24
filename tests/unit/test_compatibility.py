from app.analysis.ast_analyzer import (
    analyze_python_source,
)
from app.analysis.compatibility import (
    compare_modules,
)


def compare(
    before_source: str,
    after_source: str,
):
    before = analyze_python_source(
        before_source,
        "example.py",
    )

    after = analyze_python_source(
        after_source,
        "example.py",
    )

    return compare_modules(
        before,
        after,
    )


def categories(findings):
    return {
        finding.category
        for finding in findings
    }


def test_detects_removed_public_function():
    findings = compare(
        """
def create_user(name: str):
    pass
""",
        """
pass
""",
    )

    assert (
        "PUBLIC_API_REMOVED"
        in categories(findings)
    )


def test_ignores_removed_private_function():
    findings = compare(
        """
def _validate_user(name: str):
    pass
""",
        """
pass
""",
    )

    assert (
        "PUBLIC_API_REMOVED"
        not in categories(findings)
    )


def test_detects_required_parameter_added():
    findings = compare(
        """
def create_user(name: str):
    pass
""",
        """
def create_user(
    name: str,
    organization_id: int,
):
    pass
""",
    )

    assert (
        "REQUIRED_PARAMETER_ADDED"
        in categories(findings)
    )


def test_optional_parameter_added_is_safe():
    findings = compare(
        """
def create_user(name: str):
    pass
""",
        """
def create_user(
    name: str,
    active: bool = True,
):
    pass
""",
    )

    assert (
        "REQUIRED_PARAMETER_ADDED"
        not in categories(findings)
    )


def test_detects_parameter_removed():
    findings = compare(
        """
def create_user(
    name: str,
    age: int,
):
    pass
""",
        """
def create_user(
    name: str,
):
    pass
""",
    )

    assert (
        "PARAMETER_REMOVED"
        in categories(findings)
    )


def test_detects_parameter_reordered():
    findings = compare(
        """
def create_user(
    name: str,
    age: int,
):
    pass
""",
        """
def create_user(
    age: int,
    name: str,
):
    pass
""",
    )

    assert (
        "PARAMETER_REORDERED"
        in categories(findings)
    )


def test_parameter_removal_does_not_fake_reorder():
    findings = compare(
        """
def create_user(
    name: str,
    age: int,
    active: bool,
):
    pass
""",
        """
def create_user(
    name: str,
    active: bool,
):
    pass
""",
    )

    assert (
        "PARAMETER_REMOVED"
        in categories(findings)
    )

    assert (
        "PARAMETER_REORDERED"
        not in categories(findings)
    )


def test_detects_default_removed():
    findings = compare(
        """
def create_user(
    name: str,
    active: bool = True,
):
    pass
""",
        """
def create_user(
    name: str,
    active: bool,
):
    pass
""",
    )

    assert (
        "PARAMETER_DEFAULT_REMOVED"
        in categories(findings)
    )


def test_detects_return_annotation_change():
    findings = compare(
        """
def get_user() -> str:
    return "Marie"
""",
        """
def get_user() -> int:
    return 1
""",
    )

    assert (
        "RETURN_TYPE_CHANGED"
        in categories(findings)
    )


def test_detects_sync_to_async():
    findings = compare(
        """
def fetch_user():
    pass
""",
        """
async def fetch_user():
    pass
""",
    )

    assert (
        "ASYNC_BEHAVIOR_CHANGED"
        in categories(findings)
    )


def test_detects_async_to_sync():
    findings = compare(
        """
async def fetch_user():
    pass
""",
        """
def fetch_user():
    pass
""",
    )

    assert (
        "ASYNC_BEHAVIOR_CHANGED"
        in categories(findings)
    )


def test_ignores_self_parameter():
    findings = compare(
        """
class UserService:
    def create(
        self,
        name: str,
    ):
        pass
""",
        """
class UserService:
    def create(
        self,
        name: str,
        organization_id: int,
    ):
        pass
""",
    )

    assert (
        "REQUIRED_PARAMETER_ADDED"
        in categories(findings)
    )

    assert all(
        finding.evidence != "self"
        for finding in findings
    )


def test_unchanged_function_has_no_findings():
    source = """
def create_user(
    name: str,
    active: bool = True,
) -> bool:
    return True
"""

    findings = compare(
        source,
        source,
    )

    assert findings == []