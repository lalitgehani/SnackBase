"""Validate Function source file paths at deploy time."""

from __future__ import annotations

MAX_SOURCE_PATH_LENGTH = 255


class SourcePathError(ValueError):
    """Raised when a deploy source path is unsafe or malformed."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid source path '{path}': {reason}")


def validate_source_path(path: str) -> str:
    """Return a validated relative POSIX path or raise SourcePathError."""
    if path is None or path == "":
        raise SourcePathError(str(path), "path must be a non-empty relative POSIX path")
    if not isinstance(path, str):
        raise SourcePathError(str(path), "path must be a string")
    if "\0" in path:
        raise SourcePathError(path, "path must not contain NUL characters")
    if len(path) > MAX_SOURCE_PATH_LENGTH:
        raise SourcePathError(
            path,
            f"path must be at most {MAX_SOURCE_PATH_LENGTH} characters",
        )
    if path.startswith("/"):
        raise SourcePathError(path, "absolute paths are not allowed")
    if "\\" in path:
        raise SourcePathError(path, "backslashes are not allowed")
    parts = path.split("/")
    if any(part == "" for part in parts):
        raise SourcePathError(path, "path must not contain empty segments")
    if any(part == ".." for part in parts):
        raise SourcePathError(path, "path must not contain '..' segments")
    if any(part == "." for part in parts):
        raise SourcePathError(path, "path must not contain '.' segments")
    return path


def validate_source_files(files: dict[str, str], entrypoint: str) -> str:
    """Validate every files key and the entrypoint; return the entrypoint."""
    if not files:
        raise SourcePathError("", "deploy requires at least one file")

    for path in files:
        validate_source_path(path)

    ep = entrypoint or "handler.py"
    validate_source_path(ep)
    if ep not in files:
        raise SourcePathError(ep, "entrypoint must identify one of the submitted files")
    return ep
