"""Unit tests for function dependency pin parser."""

import pytest

from snackbase.infrastructure.functions.pin_parser import (
    PinParseError,
    parse_dependencies,
    parse_pin,
    parse_requirements_txt,
)


def test_parse_exact_pin() -> None:
    assert parse_pin("cowsay==6.1") == "cowsay==6.1"
    assert parse_pin("openai==1.66.0") == "openai==1.66.0"


def test_reject_unpinned() -> None:
    with pytest.raises(PinParseError, match="exact pin"):
        parse_pin("openai")


def test_reject_range() -> None:
    with pytest.raises(PinParseError):
        parse_pin("openai>=1.0")


def test_reject_git() -> None:
    with pytest.raises(PinParseError, match="not allowed"):
        parse_pin("git+https://github.com/x/y.git")


def test_reject_url() -> None:
    with pytest.raises(PinParseError, match="not allowed"):
        parse_pin("https://example.com/pkg.whl")


def test_requirements_txt() -> None:
    content = """
# comment
cowsay==6.1
httpx==0.28.1
"""
    assert parse_requirements_txt(content) == ["cowsay==6.1", "httpx==0.28.1"]


def test_parse_dependencies_merge_and_dedupe() -> None:
    pins = parse_dependencies(
        ["cowsay==6.0"],
        requirements_txt="cowsay==6.1\n",
        mode="open_pinned",
    )
    assert pins == ["cowsay==6.1"]


def test_allowlist_mode() -> None:
    with pytest.raises(PinParseError, match="allowlist"):
        parse_dependencies(
            ["evil==1.0"],
            mode="allowlist",
            allowlist=["cowsay"],
        )
    assert parse_dependencies(
        ["cowsay==6.1"],
        mode="allowlist",
        allowlist=["cowsay"],
    ) == ["cowsay==6.1"]


def test_default_mode_is_allowlist() -> None:
    """C-04: an unconfigured deployment must not install arbitrary PyPI packages."""
    with pytest.raises(PinParseError, match="allowlist"):
        parse_dependencies(["cowsay==6.1"])
