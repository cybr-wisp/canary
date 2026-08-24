
from app.analysis.repository_analyzer import (
    analyze_repository_sources,
    canonical_function_name,
    find_call_sites,
    module_name_from_filename,
)


def test_module_name_from_filename():
    assert (
        module_name_from_filename(
            "app/services/users.py"
        )
        == "app.services.users"
    )

    assert (
        module_name_from_filename(
            "app/services/__init__.py"
        )
        == "app.services"
    )


def test_detects_direct_imported_call():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass
""",
        "app/api.py": """
from app.users import create_user

def signup():
    create_user("Marie")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert len(calls) == 1

    assert (
        calls[0].filename
        == "app/api.py"
    )

    assert (
        calls[0].resolved_callee
        == "app.users.create_user"
    )


def test_detects_aliased_function_import():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass
""",
        "app/api.py": """
from app.users import create_user as make_user

def signup():
    make_user("Marie")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert len(calls) == 1

    assert (
        calls[0].callee
        == "make_user"
    )

    assert (
        calls[0].resolved_callee
        == "app.users.create_user"
    )


def test_detects_module_alias_call():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass
""",
        "app/api.py": """
import app.users as users

def signup():
    users.create_user("Marie")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert len(calls) == 1

    assert (
        calls[0].resolved_callee
        == "app.users.create_user"
    )


def test_detects_same_file_call():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass

def signup():
    create_user("Marie")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert len(calls) == 1

    assert (
        calls[0].enclosing_symbol
        == "signup"
    )


def test_does_not_match_unrelated_same_name():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass
""",
        "other/users.py": """
def create_user(name: str):
    pass
""",
        "app/api.py": """
from other.users import create_user

def signup():
    create_user("Marie")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert calls == []


def test_detects_multiple_cross_file_call_sites():
    sources = {
        "app/users.py": """
def create_user(name: str):
    pass
""",
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

def test_create_user():
    create_user("Test")
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/users.py"
    ].functions["create_user"]

    calls = find_call_sites(
        repository,
        defining_filename="app/users.py",
        function=function,
    )

    assert len(calls) == 3

    assert {
        call.filename
        for call in calls
    } == {
        "app/api.py",
        "app/admin.py",
        "tests/test_users.py",
    }


def test_invalid_python_is_recorded_not_crashed():
    sources = {
        "app/good.py": """
def hello():
    pass
""",
        "app/broken.py": """
def broken(
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    assert (
        "app/good.py"
        in repository.modules
    )

    assert (
        "app/broken.py"
        in repository.parse_errors
    )


def test_builds_canonical_function_name():
    sources = {
        "app/services/users.py": """
class UserService:
    def create(self, name: str):
        pass
""",
    }

    repository = (
        analyze_repository_sources(
            sources
        )
    )

    function = repository.modules[
        "app/services/users.py"
    ].functions[
        "UserService.create"
    ]

    canonical = canonical_function_name(
        "app/services/users.py",
        function,
    )

    assert canonical == (
        "app.services.users."
        "UserService.create"
    )