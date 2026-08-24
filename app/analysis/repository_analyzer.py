from __future__ import annotations

import ast

from app.analysis.ast_analyzer import (
    analyze_python_source,
)
from app.models import (
    CallSite,
    FunctionInfo,
    RepositoryAnalysis,
)


def module_name_from_filename(
    filename: str,
) -> str:
    """
    Convert a repository Python path into its import-style
    module name.

    Examples:

        app/services/users.py
            -> app.services.users

        app/services/__init__.py
            -> app.services

        users.py
            -> users
    """

    normalized = filename.replace(
        "\\",
        "/",
    )

    if not normalized.endswith(".py"):
        raise ValueError(
            f"Expected Python file, got: {filename}"
        )

    without_extension = normalized[:-3]

    parts = [
        part
        for part in without_extension.split("/")
        if part
    ]

    if parts and parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def _package_name(
    filename: str,
) -> str:
    """
    Return the package containing a Python source file.
    """

    module = module_name_from_filename(
        filename
    )

    normalized = filename.replace(
        "\\",
        "/",
    )

    if normalized.endswith("/__init__.py"):
        return module

    if "." not in module:
        return ""

    return module.rsplit(
        ".",
        1,
    )[0]


def _resolve_relative_module(
    filename: str,
    *,
    level: int,
    module: str | None,
) -> str:
    """
    Resolve a relative import against the current package.

    Examples:

        from .models import User

        from ..services import create_user
    """

    if level == 0:
        return module or ""

    package = _package_name(
        filename
    )

    parts = (
        package.split(".")
        if package
        else []
    )

    # In Python AST:
    #
    # level=1 -> current package
    # level=2 -> parent package
    # level=3 -> grandparent package
    levels_up = max(
        level - 1,
        0,
    )

    if levels_up:
        if levels_up >= len(parts):
            parts = []

        else:
            parts = parts[
                : len(parts) - levels_up
            ]

    if module:
        parts.extend(
            module.split(".")
        )

    return ".".join(parts)


def _dotted_name(
    node: ast.expr,
) -> str | None:
    """
    Convert a Name/Attribute expression into dotted notation.

    Examples:

        create_user
            -> create_user

        users.create_user
            -> users.create_user

        app.services.users.create_user
            -> app.services.users.create_user
    """

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _dotted_name(
            node.value
        )

        if parent is None:
            return None

        return (
            f"{parent}.{node.attr}"
        )

    return None


def _resolve_alias(
    callee: str,
    aliases: dict[str, str],
) -> str:
    """
    Resolve the first component of a call through the module's
    import aliases.

    Example:

        import app.services.users as users

        users.create_user()

    becomes:

        app.services.users.create_user
    """

    parts = callee.split(".")

    if not parts:
        return callee

    root = parts[0]

    target = aliases.get(
        root
    )

    if target is None:
        return callee

    remainder = parts[1:]

    if not remainder:
        return target

    return ".".join(
        [
            target,
            *remainder,
        ]
    )


class _CallSiteVisitor(ast.NodeVisitor):
    """
    Walk a Python source file and record function calls.

    Canary stores both the literal callee and a best-effort
    import-resolved callee.

    v2 also records argument structure and whether the call
    appears inside an await expression.
    """

    def __init__(
        self,
        filename: str,
    ) -> None:
        self.filename = filename

        self.aliases: dict[
            str,
            str,
        ] = {}

        self.scope: list[str] = []

        self.call_sites: list[
            CallSite
        ] = []

        self.awaited_calls: set[int] = set()

    def visit_Import(
        self,
        node: ast.Import,
    ) -> None:
        for alias in node.names:
            if alias.asname:
                bound_name = (
                    alias.asname
                )

                target = alias.name

            else:
                # `import app.services.users`
                # binds `app`, not the full dotted path.
                bound_name = (
                    alias.name.split(".")[0]
                )

                target = bound_name

            self.aliases[
                bound_name
            ] = target

        self.generic_visit(node)

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        module = _resolve_relative_module(
            self.filename,
            level=node.level,
            module=node.module,
        )

        for alias in node.names:
            if alias.name == "*":
                continue

            bound_name = (
                alias.asname
                or alias.name
            )

            if module:
                target = (
                    f"{module}.{alias.name}"
                )

            else:
                target = alias.name

            self.aliases[
                bound_name
            ] = target

        self.generic_visit(node)

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> None:
        self.scope.append(
            node.name
        )

        self.generic_visit(node)

        self.scope.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self.scope.append(
            node.name
        )

        self.generic_visit(node)

        self.scope.pop()

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self.scope.append(
            node.name
        )

        self.generic_visit(node)

        self.scope.pop()

    def visit_Await(
        self,
        node: ast.Await,
    ) -> None:
        """
        Mark direct awaited calls before visiting the call itself.

        Example:

            await fetch_user()

        allows the CallSite for fetch_user() to record:

            is_awaited=True
        """

        if isinstance(
            node.value,
            ast.Call,
        ):
            self.awaited_calls.add(
                id(node.value)
            )

        self.generic_visit(node)

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:
        callee = _dotted_name(
            node.func
        )

        if callee is not None:
            resolved = _resolve_alias(
                callee,
                self.aliases,
            )

            enclosing = (
                ".".join(self.scope)
                if self.scope
                else None
            )

            positional_argument_count = sum(
                not isinstance(
                    argument,
                    ast.Starred,
                )
                for argument in node.args
            )

            has_star_args = any(
                isinstance(
                    argument,
                    ast.Starred,
                )
                for argument in node.args
            )

            keyword_arguments = tuple(
                keyword.arg
                for keyword in node.keywords
                if keyword.arg is not None
            )

            has_star_kwargs = any(
                keyword.arg is None
                for keyword in node.keywords
            )

            self.call_sites.append(
                CallSite(
                    filename=self.filename,
                    line=node.lineno,
                    column=node.col_offset,
                    callee=callee,
                    resolved_callee=resolved,
                    enclosing_symbol=enclosing,
                    positional_argument_count=(
                        positional_argument_count
                    ),
                    keyword_arguments=(
                        keyword_arguments
                    ),
                    has_star_args=(
                        has_star_args
                    ),
                    has_star_kwargs=(
                        has_star_kwargs
                    ),
                    is_awaited=(
                        id(node)
                        in self.awaited_calls
                    ),
                )
            )

        self.generic_visit(node)


def _extract_call_sites(
    source: str,
    filename: str,
) -> list[CallSite]:
    """
    Parse one source file and return every statically visible
    call expression.
    """

    tree = ast.parse(
        source,
        filename=filename,
    )

    visitor = _CallSiteVisitor(
        filename=filename
    )

    visitor.visit(tree)

    return visitor.call_sites


def analyze_repository_sources(
    sources: dict[str, str],
) -> RepositoryAnalysis:
    """
    Build Canary's repository-level semantic index.

    `sources` maps repository paths to complete source text:

        {
            "app/users.py": "...",
            "app/api.py": "...",
        }

    Non-Python files are ignored.

    Invalid Python files are recorded in `parse_errors` rather than
    crashing the entire analysis.
    """

    result = RepositoryAnalysis()

    for filename, source in sources.items():
        if not filename.endswith(".py"):
            continue

        try:
            module = analyze_python_source(
                source,
                filename,
            )

            call_sites = (
                _extract_call_sites(
                    source,
                    filename,
                )
            )

        except (
            ValueError,
            SyntaxError,
        ) as exc:
            result.parse_errors[
                filename
            ] = str(exc)

            continue

        result.modules[
            filename
        ] = module

        result.call_sites.extend(
            call_sites
        )

    return result


def canonical_function_name(
    filename: str,
    function: FunctionInfo,
) -> str:
    """
    Return the repository-wide canonical identity of a function.

    Example:

        filename:
            app/services/users.py

        function.qualname:
            create_user

        result:
            app.services.users.create_user
    """

    module = module_name_from_filename(
        filename
    )

    if not module:
        return function.qualname

    return (
        f"{module}.{function.qualname}"
    )


def find_call_sites(
    repository: RepositoryAnalysis,
    *,
    defining_filename: str,
    function: FunctionInfo,
) -> list[CallSite]:
    """
    Find high-confidence call sites for a function.

    Canary currently recognizes:

    1. Direct imported calls

        from app.users import create_user
        create_user()

    2. Import aliases

        from app.users import create_user as make_user
        make_user()

    3. Module aliases

        import app.users as users
        users.create_user()

    4. Same-file calls

        def create_user(...):
            ...

        def signup():
            create_user(...)

    5. Class-qualified calls

        UserService.create(...)

    Instance/type inference such as:

        service.create(...)

    is intentionally not resolved yet because that requires deeper
    data-flow/type analysis.
    """

    target = canonical_function_name(
        defining_filename,
        function,
    )

    local_names = {
        function.qualname,
        function.name,
    }

    matches: list[CallSite] = []

    seen: set[
        tuple[str, int, int]
    ] = set()

    for site in repository.call_sites:
        matched = False

        # Imported/resolved call.
        if site.resolved_callee == target:
            matched = True

        # Call within the file where the API is declared.
        elif (
            site.filename
            == defining_filename
            and site.resolved_callee
            in local_names
        ):
            matched = True

        if not matched:
            continue

        key = (
            site.filename,
            site.line,
            site.column,
        )

        if key in seen:
            continue

        seen.add(key)

        matches.append(site)

    return sorted(
        matches,
        key=lambda call: (
            call.filename,
            call.line,
            call.column,
        ),
    )