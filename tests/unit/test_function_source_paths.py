"""Unit tests for Function deploy source-path validation."""

from __future__ import annotations

import pytest

from snackbase.infrastructure.functions.source_paths import (
    SourcePathError,
    validate_source_files,
    validate_source_path,
)


@pytest.mark.parametrize(
    "path",
    [
        "handler.py",
        "lib/formatters.py",
        "a" * 255,
        "requirements.txt",
    ],
)
def test_valid_paths(path: str) -> None:
    assert validate_source_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/abs.py",
        "../outside.py",
        "lib/../../outside.py",
        "lib\\evil.py",
        "a" * 256,
        "has\0nul.py",
        "lib//double.py",
        "./sneaky.py",
    ],
)
def test_invalid_paths(path: str) -> None:
    with pytest.raises(SourcePathError) as exc:
        validate_source_path(path)
    assert path == "" or path in str(exc.value) or "NUL" in str(exc.value) or "255" in str(
        exc.value
    )


def test_validate_source_files_requires_entrypoint_member() -> None:
    with pytest.raises(SourcePathError, match="entrypoint"):
        validate_source_files({"handler.py": "x"}, "missing.py")


def test_validate_source_files_ok() -> None:
    ep = validate_source_files(
        {"handler.py": "x", "lib/formatters.py": "y"},
        "lib/formatters.py",
    )
    assert ep == "lib/formatters.py"
