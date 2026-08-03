"""Unit tests for Function Python syntax preflight."""

from __future__ import annotations

import pytest

from snackbase.infrastructure.functions.syntax_preflight import (
    SyntaxPreflightError,
    validate_python_syntax,
)

VALID_ASYNC = '''
from snackbase_fn import Request, Response

async def handler(req: Request) -> Response:
    return Response.json({"ok": True})
'''

VALID_PY312 = '''
def handler(req):
    match req.method:
        case "GET":
            return {"ok": True}
        case _:
            return {"ok": False}
'''

INVALID = '''
def handler(req)
    return {}
'''


def test_valid_python_passes() -> None:
    validate_python_syntax(
        {
            "handler.py": VALID_ASYNC,
            "notes.txt": "not python",
            "config.json": "{}",
        }
    )


def test_py312_match_syntax_passes() -> None:
    validate_python_syntax({"handler.py": VALID_PY312})


def test_unavailable_imports_still_pass_syntax() -> None:
    validate_python_syntax(
        {
            "handler.py": "import totally_missing_pkg\n\ndef handler(req):\n    return {}\n"
        }
    )


def test_syntax_error_reports_file_line_column() -> None:
    with pytest.raises(SyntaxPreflightError) as exc:
        validate_python_syntax({"bad.py": INVALID, "ok.py": "x = 1\n"})
    assert exc.value.path == "bad.py"
    assert exc.value.line >= 1
    assert exc.value.column >= 1
    assert "bad.py" in str(exc.value)
