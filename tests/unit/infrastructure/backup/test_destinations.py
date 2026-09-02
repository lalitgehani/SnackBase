"""Unit tests for backup destinations (F1.1, F1.2)."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from snackbase.infrastructure.backup.destinations import (
    BackupDestination,
    BackupDestinationError,
    BackupNotFoundError,
    LocalBackupDestination,
    S3BackupDestination,
    resolve_destination,
    validate_archive_name,
)


def _error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "HeadObject")


class TestArchiveNameValidation:
    def test_rejects_path_separator(self) -> None:
        with pytest.raises(ValueError):
            validate_archive_name("a/b.zip")

    def test_rejects_parent_segment(self) -> None:
        with pytest.raises(ValueError):
            validate_archive_name("../escape.zip")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            validate_archive_name("")

    def test_accepts_plain_name(self) -> None:
        validate_archive_name("@auto_snackbase_20260902T020000.zip")


class TestLocalBackupDestination:
    async def test_list_returns_entries_newest_first(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        older = dest.base_path / "b.zip"
        newer = dest.base_path / "a.zip"
        older.write_bytes(b"older")
        newer.write_bytes(b"newer")
        past = datetime.now() - timedelta(hours=1)
        import os

        os.utime(older, (past.timestamp(), past.timestamp()))

        entries = await dest.list()

        assert [entry.name for entry in entries] == ["a.zip", "b.zip"]

    async def test_list_excludes_non_zip_files(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        (dest.base_path / "notes.txt").write_bytes(b"x")
        (dest.base_path / "a.zip").write_bytes(b"x")

        entries = await dest.list()

        assert [entry.name for entry in entries] == ["a.zip"]

    async def test_list_prefix_filters(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        (dest.base_path / "@auto_one.zip").write_bytes(b"x")
        (dest.base_path / "manual.zip").write_bytes(b"x")

        names = [entry.name for entry in await dest.list("@auto_")]

        assert names == ["@auto_one.zip"]

    async def test_list_ignores_subdirectories(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        (dest.base_path / "nested").mkdir()
        (dest.base_path / "nested" / "inner.zip").write_bytes(b"x")
        (dest.base_path / "top.zip").write_bytes(b"x")

        names = [entry.name for entry in await dest.list()]

        assert names == ["top.zip"]

    async def test_list_on_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "absent")

        assert await dest.list() == []

    async def test_write_creates_directory_and_moves_file(
        self, tmp_path: Path
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        source = tmp_path / "staging.zip"
        source.write_bytes(b"payload")

        await dest.write("backup.zip", source)

        assert (dest.base_path / "backup.zip").read_bytes() == b"payload"
        # Same filesystem: the handoff is a rename, so the staging file is gone.
        assert not source.exists()

    async def test_write_rejects_escape_names(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")

        with pytest.raises(ValueError):
            await dest.write("../escape.zip", tmp_path / "f.zip")
        with pytest.raises(ValueError):
            await dest.write("a/b.zip", tmp_path / "f.zip")

        assert not (tmp_path / "escape.zip").exists()
        if dest.base_path.exists():
            assert list(dest.base_path.iterdir()) == []

    async def test_delete_missing_raises_backup_not_found(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")

        with pytest.raises(BackupNotFoundError):
            await dest.delete("absent.zip")

    async def test_exists_false_for_absent_name(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")

        assert await dest.exists("absent.zip") is False

    async def test_round_trip_10mb_sha256_identical(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        payload = b"snackbase" * (10 * 1024 * 1024 // 9)
        source = tmp_path / "big.zip"
        source.write_bytes(payload)

        await dest.write("big.zip", source)
        restored = tmp_path / "restored.zip"
        await dest.read("big.zip", restored)

        assert hashlib.sha256(restored.read_bytes()).hexdigest() == hashlib.sha256(
            payload
        ).hexdigest()

    async def test_read_missing_raises_backup_not_found(self, tmp_path: Path) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")

        with pytest.raises(BackupNotFoundError):
            await dest.read("absent.zip", tmp_path / "out.zip")

    async def test_write_missing_source_raises_destination_error(
        self, tmp_path: Path
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")

        with pytest.raises(BackupDestinationError):
            await dest.write("x.zip", tmp_path / "missing.zip")

    async def test_write_cross_filesystem_copies_and_keeps_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        source = tmp_path / "staging.zip"
        source.write_bytes(b"payload")
        monkeypatch.setattr(
            LocalBackupDestination, "_same_filesystem", staticmethod(lambda a, b: False)
        )

        await dest.write("backup.zip", source)

        assert (dest.base_path / "backup.zip").read_bytes() == b"payload"
        # Cross filesystem: copy semantics, the staging file survives.
        assert source.exists()

    async def test_same_filesystem_detects_rename_opportunity(
        self, tmp_path: Path
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        source = tmp_path / "staging.zip"
        source.write_bytes(b"payload")

        assert LocalBackupDestination._same_filesystem(source, dest.base_path) is True

    async def test_read_to_unwritable_target_raises_destination_error(
        self, tmp_path: Path
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        (dest.base_path / "a.zip").write_bytes(b"payload")
        # A directory where the target file should be makes copyfile fail.
        target_dir = tmp_path / "out.zip"
        target_dir.mkdir()

        with pytest.raises(BackupDestinationError):
            await dest.read("a.zip", target_dir)

    async def test_delete_unlink_failure_raises_destination_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dest = LocalBackupDestination(tmp_path / "backups")
        dest.base_path.mkdir(parents=True)
        archive = dest.base_path / "a.zip"
        archive.write_bytes(b"payload")

        def raise_oserror(self: Path) -> None:
            raise OSError("denied")

        monkeypatch.setattr(Path, "unlink", raise_oserror)

        with pytest.raises(BackupDestinationError):
            await dest.delete("a.zip")


def _make_s3_destination(**overrides: object) -> tuple[S3BackupDestination, MagicMock]:
    destination = S3BackupDestination(
        bucket="sb-backups",
        region="us-east-1",
        access_key_id="key",
        secret_access_key="secret",
        **overrides,  # type: ignore[arg-type]
    )
    client = MagicMock()
    destination._client = client
    return destination, client


class TestS3BackupDestination:
    async def test_write_uses_upload_file_and_zip_content_type(
        self, tmp_path: Path
    ) -> None:
        destination, client = _make_s3_destination()
        source = tmp_path / "x.zip"
        source.write_bytes(b"data")

        await destination.write("x.zip", source)

        client.upload_file.assert_called_once()
        args, kwargs = client.upload_file.call_args
        assert args[1] == "sb-backups"
        assert args[2] == "x.zip"
        assert kwargs["ExtraArgs"] == {"ContentType": "application/zip"}
        client.put_object.assert_not_called()

    async def test_write_with_key_prefix_stores_under_prefix(
        self, tmp_path: Path
    ) -> None:
        destination, client = _make_s3_destination(key_prefix="instances/abc")
        source = tmp_path / "x.zip"
        source.write_bytes(b"data")

        await destination.write("x.zip", source)

        args, _ = client.upload_file.call_args
        assert args[2] == "instances/abc/x.zip"

    async def test_list_returns_all_pages(self) -> None:
        destination, client = _make_s3_destination()
        paginator = MagicMock()

        def paginate(**kwargs: object) -> list[dict]:
            del kwargs
            pages = []
            total = 1200
            per_page = 1000
            for page_index in range(2):
                count = min(per_page, total - page_index * per_page)
                pages.append(
                    {
                        "Contents": [
                            {
                                "Key": f"archive_{page_index * per_page + i}.zip",
                                "Size": 1,
                                "LastModified": datetime(2026, 9, 2, 0, i % 60),
                            }
                            for i in range(count)
                        ]
                    }
                )
            return pages

        paginator.paginate.side_effect = paginate
        client.get_paginator.return_value = paginator

        entries = await destination.list()

        assert len(entries) == 1200

    async def test_list_strips_configured_key_prefix(self) -> None:
        destination, client = _make_s3_destination(key_prefix="instances/abc")
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "instances/abc/x.zip",
                        "Size": 5,
                        "LastModified": datetime(2026, 9, 2, 1, 0),
                    }
                ]
            }
        ]
        client.get_paginator.return_value = paginator

        entries = await destination.list()

        paginator.paginate.assert_called_once_with(
            Bucket="sb-backups", Prefix="instances/abc/"
        )
        assert [entry.name for entry in entries] == ["x.zip"]

    async def test_list_prefix_filters_within_configured_prefix(self) -> None:
        destination, client = _make_s3_destination(key_prefix="instances/abc")
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        client.get_paginator.return_value = paginator

        await destination.list("@auto_")

        paginator.paginate.assert_called_once_with(
            Bucket="sb-backups", Prefix="instances/abc/@auto_"
        )

    async def test_read_missing_key_raises_backup_not_found(
        self, tmp_path: Path
    ) -> None:
        destination, client = _make_s3_destination()
        client.download_file.side_effect = _error("NoSuchKey")

        with pytest.raises(BackupNotFoundError):
            await destination.read("absent.zip", tmp_path / "out.zip")

    async def test_read_other_client_error_raises_destination_error(
        self, tmp_path: Path
    ) -> None:
        destination, client = _make_s3_destination()
        client.download_file.side_effect = _error("AccessDenied")

        with pytest.raises(BackupDestinationError):
            await destination.read("x.zip", tmp_path / "out.zip")

    async def test_delete_missing_raises_backup_not_found(self) -> None:
        destination, client = _make_s3_destination()
        client.head_object.side_effect = _error("404")

        with pytest.raises(BackupNotFoundError):
            await destination.delete("absent.zip")

    async def test_exists_false_on_404(self) -> None:
        destination, client = _make_s3_destination()
        client.head_object.side_effect = _error("404")

        assert await destination.exists("absent.zip") is False

    async def test_exists_true_when_head_succeeds(self) -> None:
        destination, _client = _make_s3_destination()

        assert await destination.exists("x.zip") is True

    async def test_write_ignores_upload_size_limits(self, tmp_path: Path) -> None:
        destination, client = _make_s3_destination()
        source = tmp_path / "big.zip"
        source.write_bytes(b"x" * 100)

        await destination.write("big.zip", source)

        client.upload_file.assert_called_once()

    async def test_write_upload_failure_raises_destination_error(
        self, tmp_path: Path
    ) -> None:
        destination, client = _make_s3_destination()
        client.upload_file.side_effect = _error("AccessDenied")
        source = tmp_path / "x.zip"
        source.write_bytes(b"data")

        with pytest.raises(BackupDestinationError):
            await destination.write("x.zip", source)

    async def test_list_failure_raises_destination_error(self) -> None:
        destination, client = _make_s3_destination()
        paginator = MagicMock()
        paginator.paginate.side_effect = _error("AccessDenied")
        client.get_paginator.return_value = paginator

        with pytest.raises(BackupDestinationError):
            await destination.list()

    async def test_delete_success_calls_delete_object(self) -> None:
        destination, client = _make_s3_destination()

        await destination.delete("x.zip")

        client.delete_object.assert_called_once_with(
            Bucket="sb-backups", Key="x.zip"
        )

    async def test_delete_object_failure_raises_destination_error(self) -> None:
        destination, client = _make_s3_destination()
        client.delete_object.side_effect = _error("AccessDenied")

        with pytest.raises(BackupDestinationError):
            await destination.delete("x.zip")

    async def test_exists_head_failure_raises_destination_error(self) -> None:
        destination, client = _make_s3_destination()
        client.head_object.side_effect = _error("AccessDenied")

        with pytest.raises(BackupDestinationError):
            await destination.exists("x.zip")

    async def test_client_construction_passes_credentials_and_endpoint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import boto3

        fake_client_factory = MagicMock()
        monkeypatch.setattr(boto3, "client", fake_client_factory)
        destination = S3BackupDestination(
            bucket="sb-backups",
            region="eu-west-1",
            access_key_id="key",
            secret_access_key="secret",
            key_prefix="instances/abc",
            endpoint_url="http://localhost:4566",
        )

        client = destination._get_client()

        assert client is fake_client_factory.return_value
        assert destination._client is client
        fake_client_factory.assert_called_once_with(
            "s3",
            region_name="eu-west-1",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            endpoint_url="http://localhost:4566",
        )

    async def test_client_construction_omits_absent_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import boto3

        fake_client_factory = MagicMock()
        monkeypatch.setattr(boto3, "client", fake_client_factory)
        destination = S3BackupDestination(bucket="sb-backups", region="us-east-1")

        destination._get_client()

        kwargs = fake_client_factory.call_args.kwargs
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs
        assert "endpoint_url" not in kwargs

    def test_is_backup_destination_subclass(self) -> None:
        assert issubclass(LocalBackupDestination, BackupDestination)
        assert issubclass(S3BackupDestination, BackupDestination)


class TestResolveDestination:
    async def test_missing_config_falls_back_to_local_default(
        self, db_session
    ) -> None:
        destination = await resolve_destination(db_session)

        assert isinstance(destination, LocalBackupDestination)
        assert destination.base_path == Path("./sb_data/backups")
