"""Python syntax preflight for Function deploys.

Parses ``.py`` / ``.pyi`` sources with the compile() builtin using the running
interpreter's syntax (python 3.14). Does not import, execute, or resolve
dependencies.
"""

from __future__ import annotations

import ast
import sys


class SyntaxPreflightError(ValueError):
    """Raised when a Function source file fails syntax validation."""

    def __init__(self, path: str, line: int, column: int, message: str) -> None:
        self.path = path
        self.line = line
        self.column = column
        self.message = message
        super().__init__(f"Syntax error in '{path}' at line {line}, column {column}: {message}")


def _is_python_source(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(".py") or lower.endswith(".pyi")


def validate_python_syntax(files: dict[str, str]) -> None:
    """Parse every Python source file; raise SyntaxPreflightError on failure."""
    for path, content in sorted(files.items()):
        if not _is_python_source(path):
            continue
        try:
            # compile() reports precise line/offset; mode=exec matches module sources.
            compile(content, path, "exec", dont_inherit=True)
            # Parse with the same grammar compile() used (the running interpreter).
            # Pinning an older feature_version would reject valid runtime syntax.
            ast.parse(content, filename=path, feature_version=sys.version_info[:2])
        except SyntaxError as exc:
            line = int(exc.lineno or 1)
            # offset is 1-based column when present
            column = int(exc.offset or 1)
            message = exc.msg or "invalid syntax"
            raise SyntaxPreflightError(path, line, column, message) from exc
