"""File storage service for managing file uploads and downloads.

Handles file storage operations including saving, retrieving, and deleting files.
Files are stored in account-specific directories with UUID-based filenames.
"""

from __future__ import annotations

import json
import mimetypes
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

import puremagic

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Bytes handed to the sniffer. Signatures live at the head of a file; a few KiB
# is far more than any of them needs.
SNIFF_BYTES = 4096

# Types with no magic bytes to check. Anything else must prove itself by
# signature, so a binary payload cannot claim to be one of these and slip past.
SNIFFLESS_MIME_TYPES = frozenset({"text/plain", "text/csv", "application/json"})

# Fallback extension for an allowed type the platform cannot map to one.
FALLBACK_EXTENSION = ".bin"

# Upload bodies are consumed in slices of this size. Small enough that a
# rejected upload never costs more than one slice of memory, large enough that
# a legitimate upload is not thousands of round trips.
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def size_limit_error(size: int, max_size: int) -> ValueError:
    """Build the canonical over-size rejection error.

    Shared so every path that enforces the cap — the streaming reader, the
    domain service, the storage providers — reports it identically.
    """
    return ValueError(
        f"File size ({size / (1024 * 1024):.2f}MB) exceeds maximum allowed "
        f"size ({max_size / (1024 * 1024):.2f}MB)"
    )


async def buffer_upload_within_limit(
    read: Callable[[int], Awaitable[bytes]],
    max_size: int,
    chunk_size: int = UPLOAD_CHUNK_SIZE,
) -> tuple[BinaryIO, int]:
    """Consume an upload in bounded slices, refusing it the moment it is too big.

    Reading the whole body first and checking the size afterwards costs exactly
    as much memory as accepting it would have, which makes the limit useless as
    a memory bound. Here the running total is checked after every slice, so an
    over-limit upload is abandoned mid-stream.

    Args:
        read: Awaitable reader accepting a maximum byte count, e.g.
            ``UploadFile.read``. Never called without a bound.
        max_size: Maximum accepted size in bytes.
        chunk_size: Bytes to request per read.

    Returns:
        Tuple of (rewound stream positioned at 0, total bytes read).

    Raises:
        ValueError: If the upload exceeds ``max_size``.
    """
    # Spools to disk past one chunk, so a large accepted upload does not sit in
    # memory either.
    buffered: SpooledTemporaryFile[bytes] = SpooledTemporaryFile(max_size=chunk_size)
    total = 0

    while True:
        chunk = await read(chunk_size)
        if not chunk:
            break

        total += len(chunk)
        if total > max_size:
            buffered.close()
            raise size_limit_error(total, max_size)

        buffered.write(chunk)

    buffered.seek(0)
    return buffered, total


def _sniffed_mime_types(head: bytes) -> tuple[list[str], bool]:
    """Sniff ``head`` for content signatures.

    Returns:
        Tuple of (detected MIME types, whether any signature matched at all).
        A signature can match while carrying no MIME type — an executable
        format the sniffer knows by shape but does not name — which is why the
        two answers are distinct.
    """
    try:
        matches = puremagic.magic_string(head)
    except puremagic.PureError:
        return [], False
    except Exception:  # a malformed head must not become a 500
        return [], False

    return [m.mime_type for m in matches if m.mime_type], bool(matches)


def detect_mime_type(head: bytes, declared_mime_type: str) -> str:
    """Resolve the MIME type of an upload from its content.

    ``Content-Type`` is written by the client, so an allowlist checked against
    it is advisory: any payload uploads by claiming ``image/png``. The bytes are
    the authority here, and the declared type is only accepted where there is
    nothing to check it against.

    Args:
        head: The first bytes of the upload (see ``SNIFF_BYTES``).
        declared_mime_type: The client-supplied ``Content-Type``.

    Returns:
        The MIME type the content actually is, guaranteed to be allowed.

    Raises:
        ValueError: If the declared type is not allowed, if the content is a
            format that is not allowed, or if the content cannot be what the
            client claims.
    """
    # Checked first so an honestly-declared disallowed type keeps reporting as
    # a disallowed type rather than as a content mismatch.
    if declared_mime_type not in settings.allowed_mime_types:
        raise ValueError(
            f"File type '{declared_mime_type}' is not allowed. "
            f"Allowed types: {', '.join(settings.allowed_mime_types)}"
        )

    detected_types, has_signature = _sniffed_mime_types(head)

    for detected in detected_types:
        if detected in settings.allowed_mime_types:
            return detected

    if detected_types or has_signature:
        # The content is a recognisable format, and not one that is allowed —
        # including formats the sniffer knows by shape without naming, which is
        # what an ELF binary claiming image/png looks like.
        raise ValueError(
            f"File content is not an allowed file type. "
            f"Allowed types: {', '.join(settings.allowed_mime_types)}"
        )

    # No signature at all. Only the types that have none may claim this, and the
    # bytes still have to be text.
    if declared_mime_type not in SNIFFLESS_MIME_TYPES:
        raise ValueError(
            f"File content does not match the declared type '{declared_mime_type}'"
        )

    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            f"File content does not match the declared type '{declared_mime_type}'"
        ) from None

    return declared_mime_type


def extension_for_mime_type(mime_type: str) -> str:
    """Return the filename extension for a MIME type, including the dot."""
    return mimetypes.guess_extension(mime_type) or FALLBACK_EXTENSION


def unique_filename_for(mime_type: str) -> str:
    """Build the stored filename for an upload of ``mime_type``.

    The name is a UUID and the extension comes from the detected type, so
    neither is attacker-chosen: a request cannot decide what a file is called on
    disk, which is what makes the allowlist more than advisory.
    """
    return f"{uuid.uuid4()}{extension_for_mime_type(mime_type)}"


@dataclass
class FileMetadata:
    """Metadata for a stored file."""

    filename: str
    size: int
    mime_type: str
    path: str

    def to_dict(self) -> dict[str, str | int]:
        """Convert to dictionary for JSON storage."""
        return {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "path": self.path,
        }

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> FileMetadata:
        """Create from dictionary."""
        return cls(
            filename=str(data["filename"]),
            size=int(data["size"]),
            mime_type=str(data["mime_type"]),
            path=str(data["path"]),
        )

    @classmethod
    def from_json(cls, json_str: str) -> FileMetadata:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


class FileStorageService:
    """Service for managing file storage operations."""

    def __init__(self, storage_path: str | None = None):
        """Initialize file storage service.

        Args:
            storage_path: Base path for file storage. Defaults to settings.storage_path.
        """
        self.storage_path = Path(storage_path or settings.storage_path)

    def _get_account_directory(self, account_id: str) -> Path:
        """Get the storage directory for an account.

        Args:
            account_id: The account ID.

        Returns:
            Path to the account's storage directory.
        """
        return self.storage_path / account_id

    def _ensure_directory_exists(self, directory: Path) -> None:
        """Ensure a directory exists, creating it if necessary.

        Args:
            directory: The directory path.
        """
        directory.mkdir(parents=True, exist_ok=True)

    def _generate_unique_filename(self, mime_type: str) -> str:
        """Generate a unique filename for content of ``mime_type``.

        The request-supplied filename is deliberately not consulted: keeping its
        extension would let a caller choose what the file is called on disk, and
        whether that becomes execution depends on what serves the storage
        directory — exactly the assumption an allowlist exists to remove.

        Args:
            mime_type: The MIME type detected from the content.

        Returns:
            A unique filename whose extension reflects the detected type.
        """
        return unique_filename_for(mime_type)

    def validate_file_size(self, size: int) -> None:
        """Validate file size against configured limit.

        Args:
            size: File size in bytes.

        Raises:
            ValueError: If file size exceeds the limit.
        """
        if size > settings.max_file_size:
            raise size_limit_error(size, settings.max_file_size)

    def validate_mime_type(self, mime_type: str) -> None:
        """Validate MIME type against allowed types.

        Args:
            mime_type: The MIME type to validate.

        Raises:
            ValueError: If MIME type is not allowed.
        """
        if mime_type not in settings.allowed_mime_types:
            raise ValueError(
                f"File type '{mime_type}' is not allowed. "
                f"Allowed types: {', '.join(settings.allowed_mime_types)}"
            )

    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
    ) -> FileMetadata:
        """Save a file to storage.

        Args:
            account_id: The account ID.
            file_content: The file content as a binary stream.
            filename: Original filename.
            mime_type: MIME type of the file.
            size: File size in bytes.

        Returns:
            FileMetadata object with storage information.

        Raises:
            ValueError: If file validation fails.
        """
        # Validate file
        self.validate_file_size(size)
        self.validate_mime_type(mime_type)

        # Get account directory and ensure it exists
        account_dir = self._get_account_directory(account_id)
        self._ensure_directory_exists(account_dir)

        # Generate unique filename from the (content-derived) MIME type
        unique_filename = self._generate_unique_filename(mime_type)
        file_path = account_dir / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content.read())

        # Create relative path for storage (account_id/filename)
        relative_path = f"{account_id}/{unique_filename}"

        logger.info(
            "File saved successfully",
            account_id=account_id,
            filename=filename,
            path=relative_path,
            size=size,
        )

        return FileMetadata(
            filename=filename,
            size=size,
            mime_type=mime_type,
            path=relative_path,
        )

    def get_file_path(self, account_id: str, file_path: str) -> Path:
        """Get the absolute path to a file and validate it exists.

        Args:
            account_id: The account ID.
            file_path: The relative file path (account_id/filename).

        Returns:
            Absolute path to the file.

        Raises:
            ValueError: If file path is invalid or file doesn't exist.
            FileNotFoundError: If file doesn't exist.
        """
        # Confine the resolved path to the caller's own account directory. The
        # storage root is not a sufficient boundary: a `..` segment stays inside
        # the root while landing in a sibling tenant's directory.
        account_root = self._get_account_directory(account_id).resolve()
        try:
            absolute_path = (self.storage_path / file_path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid file path: {e}")

        if not absolute_path.is_relative_to(account_root):
            raise ValueError("Invalid file path: outside the account directory")

        # Check if file exists
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return absolute_path

    def delete_file(self, account_id: str, file_path: str) -> None:
        """Delete a file from storage.

        Args:
            account_id: The account ID.
            file_path: The relative file path (account_id/filename).

        Raises:
            ValueError: If file path is invalid.
            FileNotFoundError: If file doesn't exist.
        """
        absolute_path = self.get_file_path(account_id, file_path)

        # Delete the file
        absolute_path.unlink()

        logger.info(
            "File deleted successfully",
            account_id=account_id,
            path=file_path,
        )
