"""Local filesystem storage provider."""

from pathlib import Path
from typing import BinaryIO

from snackbase.domain.services.file_storage_service import FileMetadata, FileStorageService
from snackbase.infrastructure.storage.base import StoredFile, StorageProvider


class LocalStorageProvider(StorageProvider):
    """Storage provider implementation for local filesystem storage."""

    def __init__(self, storage_path: str | None = None) -> None:
        self._service = FileStorageService(storage_path=storage_path)

    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
    ) -> FileMetadata:
        return await self._service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )

    async def get_file(self, account_id: str, file_path: str) -> StoredFile:
        absolute_path = self._service.get_file_path(account_id, file_path)
        return StoredFile(
            local_path=absolute_path,
            filename=Path(file_path).name,
        )

    async def delete_file(self, account_id: str, file_path: str) -> None:
        self._service.delete_file(account_id, file_path)

    async def test_connection(self) -> tuple[bool, str | None]:
        """Verify that the configured local storage path is writable."""
        try:
            storage_dir = self._service.storage_path
            storage_dir.mkdir(parents=True, exist_ok=True)

            probe_file = storage_dir / ".storage_provider_probe"
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink(missing_ok=True)

            return True, f"Local storage is writable at '{storage_dir}'."
        except Exception as e:
            return False, f"Local storage test failed: {str(e)}"
