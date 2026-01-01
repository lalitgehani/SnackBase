"""File storage service for managing file uploads and downloads.

Handles file storage operations including saving, retrieving, and deleting files.
Files are stored in account-specific directories with UUID-based filenames.
"""

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


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
    def from_dict(cls, data: dict[str, str | int]) -> "FileMetadata":
        """Create from dictionary."""
        return cls(
            filename=str(data["filename"]),
            size=int(data["size"]),
            mime_type=str(data["mime_type"]),
            path=str(data["path"]),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "FileMetadata":
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

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename using UUID.

        Args:
            original_filename: The original filename.

        Returns:
            A unique filename with the original extension preserved.
        """
        # Extract extension from original filename
        suffix = Path(original_filename).suffix
        # Generate UUID-based filename
        unique_name = f"{uuid.uuid4()}{suffix}"
        return unique_name

    def validate_file_size(self, size: int) -> None:
        """Validate file size against configured limit.

        Args:
            size: File size in bytes.

        Raises:
            ValueError: If file size exceeds the limit.
        """
        if size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            actual_size_mb = size / (1024 * 1024)
            raise ValueError(
                f"File size ({actual_size_mb:.2f}MB) exceeds maximum allowed "
                f"size ({max_size_mb:.2f}MB)"
            )

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

        # Generate unique filename
        unique_filename = self._generate_unique_filename(filename)
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
        # Validate that the file path starts with the account_id
        if not file_path.startswith(f"{account_id}/"):
            raise ValueError("Invalid file path: does not belong to this account")

        # Construct absolute path
        absolute_path = self.storage_path / file_path

        # Ensure the path is within the storage directory (prevent path traversal)
        try:
            absolute_path = absolute_path.resolve()
            self.storage_path.resolve()
            if not str(absolute_path).startswith(str(self.storage_path.resolve())):
                raise ValueError("Invalid file path: path traversal detected")
        except Exception as e:
            raise ValueError(f"Invalid file path: {e}")

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
