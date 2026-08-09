"""Collection-level guards for the `security` marker and directory layout (F1.3).

These run pytest in a subprocess in ``--collect-only`` mode so the assertions
are about *selection*, not about any test's outcome.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every per-surface directory the suite is organised into. A new surface must be
# added here so an empty/undiscovered package cannot go unnoticed.
SURFACE_DIRS = (
    "test_auth",
    "test_config",
    "test_endpoints",
    "test_files",
    "test_functions",
    "test_isolation",
    "test_realtime",
    "test_ssrf",
)


def _collect(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_surface_directories_exist_as_packages() -> None:
    """Each per-surface directory exists and is an importable package."""
    security_root = REPO_ROOT / "tests" / "security"
    for name in SURFACE_DIRS:
        directory = security_root / name
        assert directory.is_dir(), f"missing security surface directory: {name}"
        assert (directory / "__init__.py").is_file(), f"{name} is not a package"


def test_security_marker_selects_only_the_security_suite() -> None:
    """`-m security` collects security tests and nothing else."""
    output = _collect("-m", "security")

    selected = [line for line in output.splitlines() if "::" in line]
    assert selected, "no security tests were collected"
    assert all(line.startswith("tests/security/") for line in selected), (
        "non-security tests leaked into the security selection:\n"
        + "\n".join(line for line in selected if not line.startswith("tests/security/"))
    )


def test_not_security_excludes_the_entire_security_suite() -> None:
    """`-m "not security"` excludes every test under tests/security/."""
    output = _collect("-m", "not security")

    selected = [line for line in output.splitlines() if "::" in line]
    assert selected, "no non-security tests were collected"
    leaked = [line for line in selected if line.startswith("tests/security/")]
    assert not leaked, "security tests leaked into the non-security selection:\n" + "\n".join(
        leaked
    )
