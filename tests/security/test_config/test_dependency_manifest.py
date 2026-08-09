"""DEP-*: dependency-manifest guards (H-04).

The CI `dependency-audit` job is the real gate — it runs `pip-audit` and
`npm audit` against advisory feeds that change daily. These tests are the local
half: they pin the specific frontend versions the VAPT called out, and they
enforce the ignore-list contract so an advisory can never be silenced by
pasting its ID without a reason.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
UI_PACKAGE_JSON = REPO_ROOT / "ui" / "package.json"
PIP_AUDIT_IGNORE = REPO_ROOT / ".pip-audit-ignore"

# Minimum patched versions from the VAPT of 2026-08-09.
MINIMUM_PINS = {
    "axios": (1, 18),
    "react-router": (7, 18),
}


def _parse_minor(spec: str) -> tuple[int, int]:
    """Extract (major, minor) from a semver range such as `^1.13.2`."""
    match = re.search(r"(\d+)\.(\d+)", spec)
    assert match is not None, f"cannot parse version from {spec!r}"
    return int(match.group(1)), int(match.group(2))


def _ui_dependencies() -> dict[str, str]:
    manifest = json.loads(UI_PACKAGE_JSON.read_text())
    return {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}


@pytest.mark.parametrize(("package", "minimum"), sorted(MINIMUM_PINS.items()))
def test_dep_001_frontend_pins_meet_patched_minimum(
    package: str, minimum: tuple[int, int]
) -> None:
    """DEP-001: the frontend pins must be at or above the patched versions."""
    dependencies = _ui_dependencies()
    assert package in dependencies, f"{package} is no longer a ui/ dependency"

    assert _parse_minor(dependencies[package]) >= minimum, (
        f"{package}={dependencies[package]} is below the patched minimum "
        f"{minimum[0]}.{minimum[1]}"
    )


def test_dep_010_pip_audit_ignore_file_exists() -> None:
    """DEP-010: the ignore-list file the CI job reads must be present."""
    assert PIP_AUDIT_IGNORE.is_file()


def test_dep_011_every_ignored_advisory_carries_a_justification() -> None:
    """DEP-011: an ignore-list entry without a justification comment is invalid.

    This mirrors the check the `dependency-audit` job runs, so an unjustified
    entry fails locally before it ever reaches CI.
    """
    unjustified: list[str] = []

    for raw_line in PIP_AUDIT_IGNORE.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        advisory, separator, justification = line.partition("#")
        if not separator or not justification.strip():
            unjustified.append(advisory.strip())

    assert not unjustified, (
        f"ignore-list entries without a justification comment: {unjustified}"
    )
