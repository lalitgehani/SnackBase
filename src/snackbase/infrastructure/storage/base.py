"""Base abstractions for storage providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from snackbase.domain.services.file_storage_service import FileMetadata


@dataclass(slots=True)
class StoredFile:
    """Transport object returned by storage providers for file retrieval."""

    local_path: Path | None = None
    content: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
    ) -> FileMetadata:
        """Save a file to the provider."""
        ...

    @abstractmethod
    async def get_file(self, account_id: str, file_path: str) -> StoredFile:
        """Get a file from the provider."""
        ...

    @abstractmethod
    async def delete_file(self, account_id: str, file_path: str) -> None:
        """Delete a file from the provider."""
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str | None]:
        """Test provider connectivity and credentials."""
        ...
