"""AST-based static validator for code handed to LocalExecutor.

Runs BEFORE exec(), as a pre-check layered on top of the restricted
builtins used at exec time (defense-in-depth, not a hardened sandbox —
see LocalExecutor's docstring).
"""

from __future__ import annotations

import ast

ALLOWED_MODULES: set[str] = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot", "duckdb",
    "scipy", "scipy.stats",
    "math", "statistics", "datetime", "json", "re", "collections", "itertools",
}

# Identifiers that must never appear as a bare name in user code, even though
# some of them (e.g. __import__) must remain reachable to the interpreter
# internally for normal `import` statements to keep working.
BLOCKED_NAMES: set[str] = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit", "help",
}


class CodeValidationError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


def validate(code: str) -> None:
    """Parse and statically validate code. Raises CodeValidationError if unsafe."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise CodeValidationError(f"Syntax error: {e}", line=e.lineno) from e

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_module(alias.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            _check_module(node.module or "", node.lineno)
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES:
                raise CodeValidationError(f"Use of '{node.id}' is not allowed.", line=node.lineno)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                raise CodeValidationError(
                    f"Access to dunder attribute '{node.attr}' is not allowed.", line=node.lineno
                )


def _check_module(name: str, lineno: int) -> None:
    top = name.split(".")[0]
    if name not in ALLOWED_MODULES and top not in ALLOWED_MODULES:
        raise CodeValidationError(f"Import of '{name}' is not allowed.", line=lineno)
