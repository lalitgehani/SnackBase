"""Unit tests for the archive writer (F2.1)."""

import zipfile
from pathlib import Path

import pytest

from snackbase.infrastructure.backup.archive import (
    ArchiveWriter,
    copy_file_chunks,
    has_member,
    member_names,
    member_text,
    validate_member_paths,
)


class TestArchiveWriter:
    def test_writes_text_and_streamed_members(self, tmp_path: Path) -> None:
        archive_path = tmp_path / "out.zip"
        with ArchiveWriter(archive_path) as writer:
            writer.write_text_member("manifest.json", '{"a": 1}')
            with writer.open_member("data.db") as member:
                member.write(b"x" * 10)

        assert member_names(archive_path) == ["manifest.json", "data.db"]
        assert member_text(archive_path, "manifest.json") == '{"a": 1}'
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.read("data.db") == b"x" * 10

    def test_writes_file_tree_with_prefix(self, tmp_path: Path) -> None:
        files_dir = tmp_path / "storage"
        (files_dir / "acc-1").mkdir(parents=True)
        (files_dir / "acc-1" / "a.txt").write_text("a")
        (files_dir / "acc-1" / "sub" / "b.txt").parent.mkdir(parents=True)
        (files_dir / "acc-1" / "sub" / "b.txt").write_text("b")
        archive_path = tmp_path / "out.zip"

        with ArchiveWriter(archive_path) as writer:
            written = writer.write_file_tree(files_dir, "files", skip=set())

        assert written == 2
        names = member_names(archive_path)
        assert "files/acc-1/a.txt" in names
        assert "files/acc-1/sub/b.txt" in names

    def test_write_file_tree_skips_directories(self, tmp_path: Path) -> None:
        files_dir = tmp_path / "storage"
        (files_dir / "acc-1").mkdir(parents=True)
        (files_dir / "acc-1" / "keep.txt").write_text("keep")
        backups_inside = files_dir / "acc-1" / "backups"
        backups_inside.mkdir(parents=True)
        (backups_inside / "old.zip").write_bytes(b"old zip")
        archive_path = tmp_path / "out.zip"

        with ArchiveWriter(archive_path) as writer:
            writer.write_file_tree(files_dir, "files", skip={backups_inside})

        names = member_names(archive_path)
        assert "files/acc-1/keep.txt" in names
        assert not any("backups" in name for name in names)

    def test_missing_source_tree_writes_nothing(self, tmp_path: Path) -> None:
        archive_path = tmp_path / "out.zip"
        with ArchiveWriter(archive_path) as writer:
            written = writer.write_file_tree(
                tmp_path / "absent", "files", skip=set()
            )
        assert written == 0
        assert member_names(archive_path) == []

    def test_archive_is_deflated_zip(self, tmp_path: Path) -> None:
        archive_path = tmp_path / "out.zip"
        with ArchiveWriter(archive_path) as writer:
            writer.write_text_member("manifest.json", "x")
        with zipfile.ZipFile(archive_path) as archive:
            info = archive.getinfo("manifest.json")
            assert info.compress_type == zipfile.ZIP_DEFLATED


class TestMemberValidation:
    def test_rejects_parent_segments(self) -> None:
        with pytest.raises(ValueError, match="escapes"):
            validate_member_paths(["../evil"])

    def test_rejects_absolute_paths(self) -> None:
        with pytest.raises(ValueError, match="absolute"):
            validate_member_paths(["/etc/passwd"])

    def test_accepts_plain_paths(self) -> None:
        validate_member_paths(["manifest.json", "files/acc/a.txt"])

    def test_deeply_nested_escape_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_member_paths(["files/acc/../../../evil"])


class TestHelpers:
    def test_has_member(self, tmp_path: Path) -> None:
        archive_path = tmp_path / "out.zip"
        with ArchiveWriter(archive_path) as writer:
            writer.write_text_member("manifest.json", "{}")

        assert has_member(archive_path, "manifest.json") is True
        assert has_member(archive_path, "data.db") is False

    def test_copy_file_chunks_counts_bytes(self, tmp_path: Path) -> None:
        import io

        source = io.BytesIO(b"y" * (1024 * 1024 + 5))
        target = io.BytesIO()

        written = copy_file_chunks(source, target)

        assert written == len(target.getvalue())
        assert target.getvalue() == b"y" * (1024 * 1024 + 5)
