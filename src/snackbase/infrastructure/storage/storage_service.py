"""Storage service for resolving and using configured storage providers."""

from typing import Any, BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services.file_storage_service import FileMetadata
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.security.encryption import EncryptionService
from snackbase.infrastructure.storage.base import StoredFile, StorageProvider
from snackbase.infrastructure.storage.local_storage_provider import LocalStorageProvider
from snackbase.infrastructure.storage.s3_storage_provider import S3StorageProvider, S3StorageSettings

logger = get_logger(__name__)


class StorageService:
    """Facade service for storage provider selection and operations."""

    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"

    def __init__(
        self,
        session: AsyncSession,
        encryption_service: EncryptionService | None = None,
    ) -> None:
        self._session = session
        self._config_repo = ConfigurationRepository(session)
        self._encryption_service = encryption_service or EncryptionService(get_settings().encryption_key)
        self._local_provider = LocalStorageProvider()

    async def _get_active_system_provider(self) -> StorageProvider:
        """Resolve active system storage provider for uploads."""
        enabled_configs = await self._config_repo.list_configs(
            category="storage_providers",
            account_id=self.SYSTEM_ACCOUNT_ID,
            is_system=True,
            enabled_only=True,
        )

        if enabled_configs:
            default_config = next(
                (config for config in enabled_configs if config.is_default),
                None,
            )
            selected = default_config if default_config else enabled_configs[0]
            return self._provider_from_config(
                provider_name=selected.provider_name,
                encrypted_config=selected.config,
            )

        # If configs exist but none are enabled, fail explicitly.
        all_configs = await self._config_repo.list_configs(
            category="storage_providers",
            account_id=self.SYSTEM_ACCOUNT_ID,
            is_system=True,
            enabled_only=False,
        )
        if all_configs:
            raise ValueError(
                "No enabled system storage provider configured. "
                "Enable a storage provider in system configuration."
            )

        # Backward-compatibility: if no storage configs exist yet, fallback to local.
        if not all_configs:
            logger.warning(
                "No enabled system storage provider configured, falling back to local storage"
            )
            return self._local_provider

        return self._local_provider

    async def _get_s3_provider(self) -> StorageProvider:
        """Resolve S3 provider from system-level config for s3-prefixed file paths."""
        config = await self._config_repo.get_config(
            category="storage_providers",
            account_id=self.SYSTEM_ACCOUNT_ID,
            provider_name="s3",
            is_system=True,
        )

        if not config or not config.enabled:
            raise ValueError("S3 storage provider is not configured or enabled")

        return self._provider_from_config(
            provider_name=config.provider_name,
            encrypted_config=config.config,
        )

    def _provider_from_config(
        self, provider_name: str, encrypted_config: dict[str, Any]
    ) -> StorageProvider:
        if provider_name == "local":
            return self._local_provider

        if provider_name == "s3":
            decrypted_config = self._encryption_service.decrypt_dict(encrypted_config)
            s3_settings = S3StorageSettings(**decrypted_config)
            return S3StorageProvider(settings=s3_settings)

        raise ValueError(f"Unsupported storage provider: {provider_name}")

    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
    ) -> FileMetadata:
        provider = await self._get_active_system_provider()
        return await provider.save_file(
            account_id=account_id,
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )

    async def get_file(self, account_id: str, file_path: str) -> StoredFile:
        if file_path.startswith("s3/"):
            provider = await self._get_s3_provider()
        else:
            provider = self._local_provider
        return await provider.get_file(account_id=account_id, file_path=file_path)

    async def delete_file(self, account_id: str, file_path: str) -> None:
        if file_path.startswith("s3/"):
            provider = await self._get_s3_provider()
        else:
            provider = self._local_provider
        await provider.delete_file(account_id=account_id, file_path=file_path)
