"""Archive writer: streaming zip layout shared by every backup type.

Archive layout::

    manifest.json          at the root
    data.db                the SQLite VACUUM INTO output (physical backups)
    tables/<name>.jsonl    one JSON object per line (logical backups)
    files/<account_id>/…   the tree under settings.storage_path

ZIP_DEFLATED with compresslevel 1: record payloads are already-compressed
or incompressible, so throughput beats ratio.
"""

import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Protocol

MANIFEST_MEMBER = "manifest.json"
DATA_MEMBER = "data.db"
FILES_PREFIX = "files/"
TABLES_PREFIX = "tables/"

CHUNK_SIZE = 1024 * 1024


class ArchiveWriter:
    """Context manager over a zip file being written member by member."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._zip: zipfile.ZipFile | None = None

    def __enter__(self) -> ArchiveWriter:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._zip = zipfile.ZipFile(
            self.path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=1,
        )
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._zip is not None:
            self._zip.close()
            self._zip = None

    def write_text_member(self, name: str, text: str) -> None:
        """Write a text member (for example ``manifest.json``) in one call."""
        assert self._zip is not None, "ArchiveWriter used outside of context"
        self._zip.writestr(name, text)

    def open_member(self, name: str) -> _MemberHandle:
        """Open a member for streamed writing; close the returned handle."""
        assert self._zip is not None, "ArchiveWriter used outside of context"
        return _MemberHandle(self._zip.open(name, "w", force_zip64=True))

    def write_file_tree(self, source_dir: Path, arc_prefix: str, skip: set[Path]) -> int:
        """Copy the tree under ``source_dir`` into ``arc_prefix/…`` members.

        ``skip`` lists directory paths that must never enter the archive.
        Returns the number of files written.
        """
        assert self._zip is not None, "ArchiveWriter used outside of context"
        written = 0
        source = Path(source_dir)
        if not source.is_dir():
            return 0
        for candidate in sorted(source.rglob("*")):
            if not candidate.is_file():
                continue
            if any(skip_dir in candidate.parents for skip_dir in skip):
                continue
            relative = candidate.relative_to(source).as_posix()
            self._zip.write(candidate, f"{arc_prefix.rstrip('/')}/{relative}")
            written += 1
        return written


class _MemberHandle:
    """Streamed member writer that closes the member without closing the zip."""

    def __init__(self, member: IO[bytes]) -> None:
        self._member = member

    def write(self, data: bytes | bytearray | memoryview) -> int:
        return self._member.write(data)

    def close(self) -> None:
        self._member.close()

    def __enter__(self) -> _MemberHandle:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def validate_member_paths(names: Iterator[str]) -> None:
    """Reject absolute paths or ``..`` segments before anything is extracted.

    Raises:
        ValueError: When any member path escapes the extraction root.
    """
    for name in names:
        if name.startswith("/") or name.startswith("\\"):
            raise ValueError(f"Archive member has an absolute path: {name!r}")
        if any(part == ".." for part in Path(name).parts):
            raise ValueError(f"Archive member escapes the extraction root: {name!r}")


def member_names(archive_path: Path) -> list[str]:
    """List the members of an archive."""
    with zipfile.ZipFile(archive_path) as archive:
        return archive.namelist()


def has_member(archive_path: Path, name: str) -> bool:
    """Return whether the archive contains ``name``."""
    return name in member_names(archive_path)


def member_text(archive_path: Path, name: str) -> str:
    """Read one text member from an archive."""
    import codecs

    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(name) as handle:
            return codecs.getreader("utf-8")(handle).read()


class Writable(Protocol):
    """Anything chunk-copying can stream into (zip members, files, buffers)."""

    def write(self, data: bytes | bytearray | memoryview) -> int: ...


def copy_file_chunks(source: IO[bytes], target: Writable) -> int:
    """Copy ``source`` into ``target`` in chunks; returns the byte count."""
    written = 0
    while True:
        chunk = source.read(CHUNK_SIZE)
        if not chunk:
            break
        target.write(chunk)
        written += len(chunk)
    return written
