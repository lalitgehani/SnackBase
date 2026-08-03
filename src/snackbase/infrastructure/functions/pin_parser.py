"""Dependency pin parser for function deploys.

Only exact pins of the form ``name==version`` are accepted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# PEP 508-ish package name with exact == version
_PIN_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*(?P<version>[A-Za-z0-9][A-Za-z0-9._+!-]*)$"
)

_FORBIDDEN_MARKERS = (
    "git+",
    "http://",
    "https://",
    "file:",
    "ssh://",
    "-e ",
    "--editable",
    " @ ",
    "@git",
    "path/",
)


class PinParseError(ValueError):
    """Raised when a dependency specification is invalid."""


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_pin(spec: str) -> str:
    """Parse a single pin and return normalized ``name==version``."""
    raw = (spec or "").strip()
    if not raw or raw.startswith("#"):
        raise PinParseError("Empty dependency specification")

    lowered = raw.lower()
    for marker in _FORBIDDEN_MARKERS:
        if marker in lowered:
            raise PinParseError(
                f"Dependency '{raw}' is not allowed (git/URL/path/editable pins rejected)"
            )

    # Reject ranges and unpinned
    if any(op in raw for op in (">=", "<=", "!=", "~=", ">", "<")) and "==" not in raw:
        raise PinParseError(f"Dependency '{raw}' must be an exact pin (name==version)")
    if "==" not in raw:
        raise PinParseError(f"Dependency '{raw}' must be an exact pin (name==version)")
    if "," in raw or ";" in raw:
        raise PinParseError(f"Dependency '{raw}' must be a single exact pin without extras markers")

    match = _PIN_RE.match(raw)
    if not match:
        raise PinParseError(f"Dependency '{raw}' must be an exact pin (name==version)")

    name = match.group("name")
    version = match.group("version")
    return f"{name}=={version}"


def parse_requirements_txt(content: str) -> list[str]:
    """Parse requirements.txt content into exact pins."""
    pins: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        pins.append(parse_pin(stripped))
    return pins


def parse_dependencies(
    dependencies: Iterable[str] | None = None,
    *,
    requirements_txt: str | None = None,
    mode: str = "open_pinned",
    allowlist: Iterable[str] | None = None,
) -> list[str]:
    """Parse and validate dependency pins from deploy body and/or requirements.txt.

    Returns a de-duplicated ordered list of ``name==version`` pins.
    """
    pins: list[str] = []
    if dependencies:
        for dep in dependencies:
            pins.append(parse_pin(dep))
    if requirements_txt:
        pins.extend(parse_requirements_txt(requirements_txt))

    # De-duplicate by package name (last wins)
    by_name: dict[str, str] = {}
    order: list[str] = []
    for pin in pins:
        name = _normalize_name(pin.split("==", 1)[0])
        if name not in by_name:
            order.append(name)
        by_name[name] = pin

    result = [by_name[n] for n in order]

    if mode == "allowlist":
        allowed = {_normalize_name(a) for a in (allowlist or [])}
        for pin in result:
            name = _normalize_name(pin.split("==", 1)[0])
            if name not in allowed:
                raise PinParseError(
                    f"Package '{name}' is not on the operator dependency allowlist"
                )

    return result
