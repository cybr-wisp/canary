from app.analysis.call_validation import (
    assess_call_site,
)
from app.analysis.ast_analyzer import (
    analyze_python_source,
)
from app.models import (
    CallImpactStatus,
    CallSite,
)


def function_from(
    source: str,
):
    module = analyze_python_source(
        source,
        "app/users.py",
    )

    return module.functions[
        "create_user"
    ]


def call(
    *,
    positional: int = 0,
    keywords: tuple[str, ...] = (),
    star_args: bool = False,
    star_kwargs: bool = False,
    awaited: bool = False,
):
    return CallSite(
        filename="app/api.py",
        line=10,
        column=4,
        callee="create_user",
        resolved_callee=(
            "app.users.create_user"
        ),
        positional_argument_count=positional,
        keyword_arguments=keywords,
        has_star_args=star_args,
        has_star_kwargs=star_kwargs,
        is_awaited=awaited,
    )


def test_required_parameter_added_breaks_old_call():
    before = function_from(
        """
def create_user(name: str):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""
    )

    result = assess_call_site(
        category="REQUIRED_PARAMETER_ADDED",
        call=call(positional=1),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.BREAKS
    )


def test_updated_call_is_unaffected():
    before = function_from(
        """
def create_user(name: str):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""
    )

    result = assess_call_site(
        category="REQUIRED_PARAMETER_ADDED",
        call=call(
            positional=1,
            keywords=(
                "organization_id",
            ),
        ),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.UNAFFECTED
    )


def test_kwargs_make_result_unknown():
    before = function_from(
        """
def create_user(name: str):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    name: str,
    organization_id: int,
):
    pass
"""
    )

    result = assess_call_site(
        category="REQUIRED_PARAMETER_ADDED",
        call=call(
            positional=1,
            star_kwargs=True,
        ),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.UNKNOWN
    )


def test_removed_parameter_breaks_keyword_call():
    before = function_from(
        """
def create_user(
    name: str,
    active: bool = True,
):
    pass
"""
    )

    after = function_from(
        """
def create_user(name: str):
    pass
"""
    )

    result = assess_call_site(
        category="PARAMETER_REMOVED",
        call=call(
            positional=1,
            keywords=("active",),
        ),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.BREAKS
    )


def test_default_removed_breaks_missing_argument():
    before = function_from(
        """
def create_user(
    name: str,
    active: bool = True,
):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    name: str,
    active: bool,
):
    pass
"""
    )

    result = assess_call_site(
        category="PARAMETER_DEFAULT_REMOVED",
        call=call(positional=1),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.BREAKS
    )


def test_reordered_positional_arguments_break():
    before = function_from(
        """
def create_user(
    name: str,
    age: int,
):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    age: int,
    name: str,
):
    pass
"""
    )

    result = assess_call_site(
        category="PARAMETER_REORDERED",
        call=call(positional=2),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.BREAKS
    )


def test_reordered_keyword_call_is_unaffected():
    before = function_from(
        """
def create_user(
    name: str,
    age: int,
):
    pass
"""
    )

    after = function_from(
        """
def create_user(
    age: int,
    name: str,
):
    pass
"""
    )

    result = assess_call_site(
        category="PARAMETER_REORDERED",
        call=call(
            keywords=(
                "name",
                "age",
            )
        ),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.UNAFFECTED
    )


def test_sync_to_async_breaks_unawaited_call():
    before = function_from(
        """
def create_user():
    pass
"""
    )

    after = function_from(
        """
async def create_user():
    pass
"""
    )

    result = assess_call_site(
        category="ASYNC_BEHAVIOR_CHANGED",
        call=call(),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.BREAKS
    )


def test_sync_to_async_awaited_call_is_unaffected():
    before = function_from(
        """
def create_user():
    pass
"""
    )

    after = function_from(
        """
async def create_user():
    pass
"""
    )

    result = assess_call_site(
        category="ASYNC_BEHAVIOR_CHANGED",
        call=call(
            awaited=True
        ),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.UNAFFECTED
    )


def test_return_type_change_is_unknown():
    before = function_from(
        """
def create_user() -> str:
    return "user"
"""
    )

    after = function_from(
        """
def create_user() -> int:
    return 1
"""
    )

    result = assess_call_site(
        category="RETURN_TYPE_CHANGED",
        call=call(),
        before=before,
        after=after,
    )

    assert (
        result.status
        == CallImpactStatus.UNKNOWN
    )