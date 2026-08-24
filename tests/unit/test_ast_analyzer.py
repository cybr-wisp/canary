
from app.analysis.ast_analyzer import (
    analyze_python_source,
)


def test_extracts_function_signature():
    source = """
def create_user(
    name: str,
    age: int = 18,
) -> bool:
    return True
"""

    result = analyze_python_source(
        source,
        "users.py",
    )

    function = result.functions[
        "create_user"
    ]

    assert function.name == "create_user"

    assert function.qualname == "create_user"

    assert function.is_public is True

    assert function.return_annotation == "bool"

    assert len(function.parameters) == 2

    assert function.parameters[0].name == "name"

    assert (
        function.parameters[0].annotation
        == "str"
    )

    assert (
        function.parameters[0].has_default
        is False
    )

    assert function.parameters[1].name == "age"

    assert (
        function.parameters[1].annotation
        == "int"
    )

    assert (
        function.parameters[1].has_default
        is True
    )


def test_extracts_async_function():
    source = """
async def fetch_user(user_id: int):
    pass
"""

    result = analyze_python_source(
        source,
        "client.py",
    )

    function = result.functions[
        "fetch_user"
    ]

    assert function.is_async is True


def test_extracts_class_methods():
    source = """
class UserService:
    def create(self, name: str):
        pass

    def _validate(self, name: str):
        pass
"""

    result = analyze_python_source(
        source,
        "services.py",
    )

    create = result.functions[
        "UserService.create"
    ]

    validate = result.functions[
        "UserService._validate"
    ]

    assert create.is_public is True

    assert validate.is_public is False


def test_extracts_imports():
    source = """
import os
import requests

from app.models import User
from app.services.auth import authenticate
"""

    result = analyze_python_source(
        source,
        "example.py",
    )

    assert "os" in result.imports
    assert "requests" in result.imports
    assert "app.models" in result.imports

    assert (
        "app.services.auth"
        in result.imports
    )


def test_extracts_keyword_only_parameters():
    source = """
def create_user(
    name: str,
    *,
    active: bool = True,
    role: str,
):
    pass
"""

    result = analyze_python_source(
        source,
        "users.py",
    )

    function = result.functions[
        "create_user"
    ]

    active = function.parameters[1]
    role = function.parameters[2]

    assert active.kind == "keyword_only"
    assert active.has_default is True

    assert role.kind == "keyword_only"
    assert role.has_default is False


def test_extracts_varargs_and_kwargs():
    source = """
def dispatch(
    event,
    *args,
    **kwargs,
):
    pass
"""

    result = analyze_python_source(
        source,
        "events.py",
    )

    parameters = result.functions[
        "dispatch"
    ].parameters

    assert parameters[1].kind == "var_positional"

    assert parameters[2].kind == "var_keyword"


def test_rejects_invalid_python():
    source = """
def broken(
"""

    try:
        analyze_python_source(
            source,
            "broken.py",
        )

    except ValueError as exc:
        assert "Could not parse" in str(exc)

    else:
        raise AssertionError(
            "Expected ValueError"
        )