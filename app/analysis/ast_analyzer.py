
from __future__ import annotations

import ast

from app.models import (
    FunctionInfo,
    ModuleAnalysis,
    ParameterInfo,
)


def _annotation_text(
    node: ast.expr | None,
) -> str | None:
    """
    Convert an AST annotation back into readable Python source.
    """

    if node is None:
        return None

    return ast.unparse(node)


def _extract_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ParameterInfo, ...]:
    """
    Convert a function's AST arguments into normalized ParameterInfo
    objects.

    Handles:

    - positional-only parameters
    - regular positional parameters
    - *args
    - keyword-only parameters
    - **kwargs
    - default values
    - type annotations
    """

    parameters: list[ParameterInfo] = []

    positional = [
        *node.args.posonlyargs,
        *node.args.args,
    ]

    positional_defaults = node.args.defaults

    default_start = (
        len(positional)
        - len(positional_defaults)
    )

    posonly_count = len(node.args.posonlyargs)

    for index, argument in enumerate(positional):
        has_default = index >= default_start

        kind = (
            "positional_only"
            if index < posonly_count
            else "positional_or_keyword"
        )

        parameters.append(
            ParameterInfo(
                name=argument.arg,
                kind=kind,
                has_default=has_default,
                annotation=_annotation_text(
                    argument.annotation
                ),
            )
        )

    if node.args.vararg is not None:
        parameters.append(
            ParameterInfo(
                name=node.args.vararg.arg,
                kind="var_positional",
                has_default=False,
                annotation=_annotation_text(
                    node.args.vararg.annotation
                ),
            )
        )

    for argument, default in zip(
        node.args.kwonlyargs,
        node.args.kw_defaults,
        strict=True,
    ):
        parameters.append(
            ParameterInfo(
                name=argument.arg,
                kind="keyword_only",
                has_default=default is not None,
                annotation=_annotation_text(
                    argument.annotation
                ),
            )
        )

    if node.args.kwarg is not None:
        parameters.append(
            ParameterInfo(
                name=node.args.kwarg.arg,
                kind="var_keyword",
                has_default=False,
                annotation=_annotation_text(
                    node.args.kwarg.annotation
                ),
            )
        )

    return tuple(parameters)


class _SymbolVisitor(ast.NodeVisitor):
    """
    Walk a Python AST and build a lightweight symbol index.
    """

    def __init__(self, filename: str) -> None:
        self.analysis = ModuleAnalysis(
            filename=filename
        )

        self.scope: list[str] = []

    def _register_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        is_async: bool,
    ) -> None:
        qualname = ".".join(
            [
                *self.scope,
                node.name,
            ]
        )

        function = FunctionInfo(
            name=node.name,
            qualname=qualname,
            line=node.lineno,
            is_async=is_async,
            is_public=not node.name.startswith("_"),
            parameters=_extract_parameters(node),
            return_annotation=_annotation_text(
                node.returns
            ),
        )

        self.analysis.functions[
            qualname
        ] = function

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self._register_function(
            node,
            is_async=False,
        )

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._register_function(
            node,
            is_async=True,
        )

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> None:
        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()

    def visit_Import(
        self,
        node: ast.Import,
    ) -> None:
        for alias in node.names:
            self.analysis.imports.add(
                alias.name
            )

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        if node.module is None:
            return

        self.analysis.imports.add(
            node.module
        )


def analyze_python_source(
    source: str,
    filename: str,
) -> ModuleAnalysis:
    """
    Parse a complete Python source file and return its public
    structural information.

    This is the foundation of Canary v2's semantic analysis.
    """

    try:
        tree = ast.parse(
            source,
            filename=filename,
        )

    except SyntaxError as exc:
        raise ValueError(
            f"Could not parse {filename}: {exc}"
        ) from exc

    visitor = _SymbolVisitor(
        filename=filename
    )

    visitor.visit(tree)

    return visitor.analysis