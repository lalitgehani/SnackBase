"""CFG-BUILD-*: build/runtime configuration invariants (M-09).

Two ways the container can differ from what CI validated:

* **Python version drift.** ``.python-version`` pins the interpreter every
  local run and every CI job uses. The Dockerfile names its own base image. If
  the two disagree, the test suite proves nothing about the artefact that
  actually ships — code that type-checks and passes on one minor can fail to
  import on another.
* **Unpinned base images.** A floating tag such as ``python:3.12-slim`` resolves
  to whatever the registry serves at build time, so two builds of the same
  commit are not the same image. Digest pinning is what makes a build
  reproducible and what lets a compromised upstream tag be detected.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = REPO_ROOT / "Dockerfile"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"
PYPROJECT = REPO_ROOT / "pyproject.toml"

_FROM_RE = re.compile(r"^FROM\s+(?P<image>\S+)", re.MULTILINE)
_PYTHON_IMAGE_RE = re.compile(r"^python:(?P<major>\d+)\.(?P<minor>\d+)")


def _declared_python_minor() -> tuple[int, int]:
    major, minor = PYTHON_VERSION_FILE.read_text().strip().split(".")[:2]
    return int(major), int(minor)


def _dockerfile_from_images() -> list[str]:
    return _FROM_RE.findall(DOCKERFILE.read_text())


def _dockerfile_python_minors() -> list[tuple[int, int]]:
    minors: list[tuple[int, int]] = []
    for image in _dockerfile_from_images():
        match = _PYTHON_IMAGE_RE.match(image)
        if match:
            minors.append((int(match.group("major")), int(match.group("minor"))))
    return minors


def test_cfg_build_001_python_version_file_is_parseable() -> None:
    """CFG-BUILD-001: `.python-version` declares a concrete major.minor."""
    assert _declared_python_minor() >= (3, 12)


def test_cfg_build_002_requires_python_covers_the_declared_version() -> None:
    """CFG-BUILD-002: `requires-python` must admit the pinned interpreter."""
    metadata = tomllib.loads(PYPROJECT.read_text())
    requires_python = metadata["project"]["requires-python"]
    match = re.search(r"(\d+)\.(\d+)", requires_python)
    assert match is not None, requires_python

    floor = (int(match.group(1)), int(match.group(2)))
    assert _declared_python_minor() >= floor, (
        f"`.python-version` {_declared_python_minor()} is below "
        f"requires-python {requires_python}"
    )


@pytest.mark.xfail(reason="M-09 fix pending", strict=True)
def test_cfg_build_010_dockerfile_python_matches_declared_version() -> None:
    """CFG-BUILD-010: the runtime image must use the pinned Python minor."""
    declared = _declared_python_minor()
    dockerfile_minors = _dockerfile_python_minors()
    assert dockerfile_minors, "no python: base image found in the Dockerfile"

    mismatched = [minor for minor in dockerfile_minors if minor != declared]
    assert not mismatched, (
        f"Dockerfile builds on Python {mismatched} but the project pins "
        f"{declared[0]}.{declared[1]} — CI validates an interpreter that never ships"
    )


@pytest.mark.xfail(reason="M-09 fix pending", strict=True)
def test_cfg_build_011_base_images_are_digest_pinned() -> None:
    """CFG-BUILD-011: every base image must be pinned by digest."""
    floating = [
        image
        for image in _dockerfile_from_images()
        if "@sha256:" not in image and not image.startswith("$")
    ]

    assert not floating, (
        f"base images are not digest-pinned, so the same commit can build "
        f"different images: {floating}"
    )
