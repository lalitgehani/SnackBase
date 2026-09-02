"""Backup archive destinations: local directory and S3-compatible object storage.

A ``BackupDestination`` is the narrow interface the backup engine sees. It is
deliberately separate from ``snackbase.infrastructure.storage``: that subsystem
enforces ``max_file_size`` and a mime allowlist, renames uploads, and buffers
bodies in memory — correct for user file uploads and wrong for multi-gigabyte
archives. Archive storage needs streaming moves, unbounded sizes, and a
listing operation for retention pruning.
"""

import asyncio
import os
import shutil
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.security.encryption import EncryptionService

logger = get_logger(__name__)

#: Default on-disk location for archives when no configuration exists.
DEFAULT_BACKUP_DIR = "./sb_data/backups"

#: Configuration category / provider that stores backup settings (F1.3).
BACKUP_SETTINGS_CATEGORY = "backup_settings"
BACKUP_SETTINGS_PROVIDER_NAME = "backup"


class BackupError(Exception):
    """Base class for backup subsystem errors."""


class BackupNotFoundError(BackupError):
    """Raised when an archive does not exist at the destination."""


class BackupExistsError(BackupError):
    """Raised when an operation would overwrite an existing archive."""


class BackupDestinationError(BackupError):
    """Raised when a destination read, write, list, or delete fails."""


class BackupConfigurationError(BackupError):
    """Raised when the backup configuration is incomplete or contradictory."""


class BackupInProgressError(BackupError):
    """Raised when a backup or restore is requested while another is in flight.

    Carries the in-flight operation kind and archive name so the API can report
    which operation is running.
    """

    def __init__(self, operation: str, name: str) -> None:
        self.operation = operation
        self.name = name
        super().__init__(
            f"A {operation} of {name!r} is already in progress"
        )


class UnsupportedEngineError(BackupError):
    """Raised when an operation is attempted against an unsupported database engine."""


def validate_archive_name(name: str) -> None:
    """Reject archive names that could escape the destination namespace.

    A name is a flat file/object key: no path separators and no ``..`` segments.

    Raises:
        ValueError: If the name is empty, contains a path separator, or
            contains ``..``.
    """
    if not name:
        raise ValueError("Archive name must not be empty")
    if "/" in name or "\\" in name or os.sep in name:
        raise ValueError(f"Archive name must not contain path separators: {name!r}")
    if ".." in name:
        raise ValueError(f"Archive name must not contain '..': {name!r}")


def _naive_utc(timestamp: datetime) -> datetime:
    """Normalise a timestamp to naive UTC, the convention used by the scheduler."""
    if timestamp.tzinfo is not None:
        return timestamp.astimezone(UTC).replace(tzinfo=None)
    return timestamp


@dataclass(frozen=True)
class BackupEntry:
    """A single archive stored at a destination."""

    name: str
    size: int
    modified: datetime  # naive UTC


class BackupDestination(ABC):
    """Abstract store for backup archives."""

    @abstractmethod
    async def write(self, name: str, local_path: Path) -> None:
        """Stream a local file to the destination under ``name``."""

    @abstractmethod
    async def read(self, name: str, local_path: Path) -> None:
        """Stream the stored archive ``name`` to a local path."""

    @abstractmethod
    async def list(self, prefix: str = "") -> list[BackupEntry]:
        """List stored archives whose name starts with ``prefix``, newest first."""

    @abstractmethod
    async def delete(self, name: str) -> None:
        """Delete the archive ``name``."""

    @abstractmethod
    async def exists(self, name: str) -> bool:
        """Return whether the archive ``name`` exists."""

    def open_download_stream(self, name: str) -> Iterator[bytes]:
        """Yield the archive ``name`` in chunks for HTTP download.

        Concrete on both implementations so a download never buffers an
        archive in memory. S3 clients return their body object directly
        rather than downloading to a temp file first.
        """
        raise NotImplementedError

    def read_sync(self, name: str, local_path: Path) -> None:
        """Blocking variant of :meth:`read` for pre-boot use.

        The restore executor runs before the event loop is serving and may
        not have a loop to await; blocking I/O is exactly right there.
        """
        raise NotImplementedError


#: Chunk size for streaming downloads (1 MiB).
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class LocalBackupDestination(BackupDestination):
    """Archive destination rooted at a configurable directory."""

    def __init__(self, base_path: str | Path = DEFAULT_BACKUP_DIR) -> None:
        self.base_path = Path(base_path)

    def _ensure_dir(self) -> Path:
        self.base_path.mkdir(parents=True, exist_ok=True)
        return self.base_path

    def _path_for(self, name: str) -> Path:
        validate_archive_name(name)
        return self.base_path / name

    async def write(self, name: str, local_path: Path) -> None:
        destination_dir = self._ensure_dir()
        validate_archive_name(name)
        source = Path(local_path)
        destination = destination_dir / name
        try:
            if self._same_filesystem(source, destination_dir):
                # Same filesystem: the handoff is a rename, not a copy.
                os.replace(source, destination)
            else:
                # copyfile streams in chunks; it never loads the archive.
                shutil.copyfile(source, destination)
        except FileNotFoundError as exc:
            raise BackupDestinationError(
                f"Archive source file not found: {source}"
            ) from exc
        except OSError as exc:
            raise BackupDestinationError(
                f"Failed to write archive {name!r} to {destination_dir}: {exc}"
            ) from exc

    @staticmethod
    def _same_filesystem(source: Path, destination_dir: Path) -> bool:
        return source.stat().st_dev == destination_dir.stat().st_dev

    async def read(self, name: str, local_path: Path) -> None:
        self.read_sync(name, local_path)

    def read_sync(self, name: str, local_path: Path) -> None:
        source = self._path_for(name)
        if not source.is_file():
            raise BackupNotFoundError(f"Archive not found: {name}")
        try:
            shutil.copyfile(source, Path(local_path))
        except OSError as exc:
            raise BackupDestinationError(
                f"Failed to read archive {name!r} from {self.base_path}: {exc}"
            ) from exc

    async def list(self, prefix: str = "") -> list[BackupEntry]:
        if not self.base_path.is_dir():
            return []
        entries: list[BackupEntry] = []
        try:
            candidates = list(self.base_path.iterdir())
        except OSError as exc:
            raise BackupDestinationError(
                f"Failed to list archives in {self.base_path}: {exc}"
            ) from exc
        for candidate in candidates:
            if not candidate.is_file() or not candidate.name.endswith(".zip"):
                continue
            if prefix and not candidate.name.startswith(prefix):
                continue
            try:
                stat = candidate.stat()
            except OSError as exc:
                raise BackupDestinationError(
                    f"Failed to stat archive {candidate.name!r}: {exc}"
                ) from exc
            entries.append(
                BackupEntry(
                    name=candidate.name,
                    size=stat.st_size,
                    modified=_naive_utc(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
                )
            )
        entries.sort(key=lambda entry: entry.modified, reverse=True)
        return entries

    async def delete(self, name: str) -> None:
        target = self._path_for(name)
        if not target.is_file():
            raise BackupNotFoundError(f"Archive not found: {name}")
        try:
            target.unlink()
        except OSError as exc:
            raise BackupDestinationError(
                f"Failed to delete archive {name!r}: {exc}"
            ) from exc

    async def exists(self, name: str) -> bool:
        return self._path_for(name).is_file()

    def open_download_stream(self, name: str) -> Iterator[bytes]:
        validate_archive_name(name)
        path = self.base_path / name
        if not path.is_file():
            raise BackupNotFoundError(f"Archive not found: {name}")

        def _chunks() -> Iterator[bytes]:
            with open(path, "rb") as handle:
                while True:
                    chunk = handle.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk

        return _chunks()


class S3BackupDestination(BackupDestination):
    """Archive destination for S3 and S3-compatible object stores.

    Uses boto3's managed transfer APIs (multipart, retry, concurrency) so large
    archives move without being held in memory, and never applies the user
    upload limits from settings.
    """

    def __init__(
        self,
        *,
        bucket: str,
        region: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        key_prefix: str = "",
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.key_prefix = key_prefix.strip("/")
        self.endpoint_url = endpoint_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            client_kwargs: dict[str, Any] = {"region_name": self.region}
            if self.access_key_id is not None:
                client_kwargs["aws_access_key_id"] = self.access_key_id
            if self.secret_access_key is not None:
                client_kwargs["aws_secret_access_key"] = self.secret_access_key
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            self._client = boto3.client("s3", **client_kwargs)
        return self._client

    def _object_key(self, name: str) -> str:
        validate_archive_name(name)
        if self.key_prefix:
            return f"{self.key_prefix}/{name}"
        return name

    def _list_prefix(self, prefix: str) -> str:
        if self.key_prefix and prefix:
            return f"{self.key_prefix}/{prefix}"
        if self.key_prefix:
            return f"{self.key_prefix}/"
        return prefix

    @staticmethod
    def _is_not_found(exc: ClientError) -> bool:
        code = exc.response.get("Error", {}).get("Code", "")
        return code in {"404", "NoSuchKey", "NotFound"}

    async def write(self, name: str, local_path: Path) -> None:
        key = self._object_key(name)
        try:
            await asyncio.to_thread(
                self._get_client().upload_file,
                str(local_path),
                self.bucket,
                key,
                ExtraArgs={"ContentType": "application/zip"},
            )
        except (ClientError, BotoCoreError) as exc:
            raise BackupDestinationError(
                f"Failed to upload archive {name!r} to S3: {exc}"
            ) from exc

    async def read(self, name: str, local_path: Path) -> None:
        await asyncio.to_thread(self.read_sync, name, local_path)

    def read_sync(self, name: str, local_path: Path) -> None:
        key = self._object_key(name)
        try:
            self._get_client().download_file(
                self.bucket,
                key,
                str(local_path),
            )
        except ClientError as exc:
            if self._is_not_found(exc):
                raise BackupNotFoundError(f"Archive not found: {name}") from exc
            raise BackupDestinationError(
                f"Failed to download archive {name!r} from S3: {exc}"
            ) from exc
        except BotoCoreError as exc:
            raise BackupDestinationError(
                f"Failed to download archive {name!r} from S3: {exc}"
            ) from exc

    async def list(self, prefix: str = "") -> list[BackupEntry]:
        paginator = self._get_client().get_paginator("list_objects_v2")
        entries: list[BackupEntry] = []
        try:
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self._list_prefix(prefix)):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    name = key
                    if self.key_prefix:
                        if not key.startswith(f"{self.key_prefix}/"):
                            continue
                        name = key[len(self.key_prefix) + 1 :]
                    if not name.endswith(".zip"):
                        continue
                    entries.append(
                        BackupEntry(
                            name=name,
                            size=int(obj["Size"]),
                            modified=_naive_utc(obj["LastModified"]),
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            raise BackupDestinationError(
                f"Failed to list archives in S3 bucket {self.bucket!r}: {exc}"
            ) from exc
        entries.sort(key=lambda entry: entry.modified, reverse=True)
        return entries

    async def delete(self, name: str) -> None:
        key = self._object_key(name)
        client = self._get_client()
        try:
            await asyncio.to_thread(client.head_object, Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_not_found(exc):
                raise BackupNotFoundError(f"Archive not found: {name}") from exc
            raise BackupDestinationError(
                f"Failed to delete archive {name!r} from S3: {exc}"
            ) from exc
        except BotoCoreError as exc:
            raise BackupDestinationError(
                f"Failed to delete archive {name!r} from S3: {exc}"
            ) from exc
        try:
            await asyncio.to_thread(client.delete_object, Bucket=self.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise BackupDestinationError(
                f"Failed to delete archive {name!r} from S3: {exc}"
            ) from exc

    async def exists(self, name: str) -> bool:
        key = self._object_key(name)
        try:
            await asyncio.to_thread(
                self._get_client().head_object, Bucket=self.bucket, Key=key
            )
        except ClientError as exc:
            if self._is_not_found(exc):
                return False
            raise BackupDestinationError(
                f"Failed to check archive {name!r} in S3: {exc}"
            ) from exc
        except BotoCoreError as exc:
            raise BackupDestinationError(
                f"Failed to check archive {name!r} in S3: {exc}"
            ) from exc
        return True

    def open_download_stream(self, name: str) -> Iterator[bytes]:
        key = self._object_key(name)
        try:
            response = self._get_client().get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_not_found(exc):
                raise BackupNotFoundError(f"Archive not found: {name}") from exc
            raise BackupDestinationError(
                f"Failed to open archive {name!r} from S3: {exc}"
            ) from exc
        except BotoCoreError as exc:
            raise BackupDestinationError(
                f"Failed to open archive {name!r} from S3: {exc}"
            ) from exc
        body = response["Body"]

        def _chunks() -> Iterator[bytes]:
            try:
                yield from body.iter_chunks(DOWNLOAD_CHUNK_SIZE)
            finally:
                body.close()

        return _chunks()


async def resolve_destination(session: AsyncSession) -> BackupDestination:
    """Resolve the configured backup destination from ``backup_settings``.

    Reads the system-level configuration, decrypting credentials through the
    existing configuration encryption path. When no ``backup_settings`` row
    exists, falls back to a local destination at ``./sb_data/backups`` rather
    than raising, so a fresh instance is protected by default.

    Raises:
        BackupConfigurationError: When the configuration selects S3 without a
            bucket, or names an unknown destination type.
    """
    settings = get_settings()
    from snackbase.core.configuration.config_registry import ConfigurationRegistry
    from snackbase.infrastructure.configuration.providers.backup.backup_settings import (
        BackupSettingsConfiguration,
    )

    provider = BackupSettingsConfiguration()
    registry = ConfigurationRegistry(EncryptionService(settings.encryption_key))
    repository = ConfigurationRepository(session)
    config = await registry.get_effective_config(
        provider.category,
        ConfigurationRegistry.SYSTEM_ACCOUNT_ID,
        provider.provider_name,
        repository,
    )

    if not config:
        return LocalBackupDestination(DEFAULT_BACKUP_DIR)

    destination_type = str(config.get("destination") or "local")
    if destination_type == "local":
        return LocalBackupDestination(str(config.get("local_path") or DEFAULT_BACKUP_DIR))
    if destination_type == "s3":
        bucket = config.get("s3_bucket")
        if not bucket:
            raise BackupConfigurationError(
                "Backup destination is set to S3 but s3_bucket is not configured"
            )
        return S3BackupDestination(
            bucket=str(bucket),
            region=str(config.get("s3_region") or "us-east-1"),
            access_key_id=_optional_str(config.get("s3_access_key_id")),
            secret_access_key=_optional_str(config.get("s3_secret_access_key")),
            key_prefix=str(config.get("s3_key_prefix") or ""),
            endpoint_url=_optional_str(config.get("s3_endpoint_url")),
        )
    raise BackupConfigurationError(f"Unknown backup destination type: {destination_type!r}")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
