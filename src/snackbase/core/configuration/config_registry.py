"""Configuration registry for managing provider configurations."""

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.security.encryption import EncryptionService


@dataclass
class ProviderDefinition:
    """Definition of a configuration provider."""

    category: str
    name: str
    display_name: str
    logo_url: Optional[str] = None
    config_schema: Optional[Dict[str, Any]] = None
    is_builtin: bool = False


@dataclass
class CachedConfig:
    """Cached effective configuration."""

    config: Optional[Dict[str, Any]]
    expires_at: float


class ConfigurationRegistry:
    """Registry for managing and resolving hierarchical provider configurations.

    Supports registration of provider definitions and hierarchical resolution
    (account-level override -> system-level fallback) with caching.
    """

    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
    CACHE_TTL = 300  # 5 minutes in seconds

    def __init__(
        self,
        encryption_service: EncryptionService,
    ) -> None:
        """Initialize the registry.

        Args:
            encryption_service: Encryption service for sensitive data.
        """
        self.encryption_service = encryption_service
        self._provider_definitions: Dict[str, ProviderDefinition] = {}
        self._cache: Dict[str, CachedConfig] = {}

    def register_provider_definition(
        self,
        category: str,
        name: str,
        display_name: str,
        logo_url: Optional[str] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        is_builtin: bool = False,
    ) -> None:
        """Register a new provider definition.

        Args:
            category: Provider category.
            name: Provider identifier.
            display_name: Human-readable name.
            logo_url: Optional path to logo.
            config_schema: Optional JSON Schema for validation.
            is_builtin: Whether this is a built-in provider.
        """
        key = f"{category}:{name}"
        self._provider_definitions[key] = ProviderDefinition(
            category=category,
            name=name,
            display_name=display_name,
            logo_url=logo_url,
            config_schema=config_schema,
            is_builtin=is_builtin,
        )

    def get_provider_definition(self, category: str, name: str) -> Optional[ProviderDefinition]:
        """Retrieve a provider definition.

        Args:
            category: Provider category.
            name: Provider identifier.

        Returns:
            Provider definition if found, None otherwise.
        """
        return self._provider_definitions.get(f"{category}:{name}")

    def list_provider_definitions(self, category: Optional[str] = None) -> List[ProviderDefinition]:
        """List all registered provider definitions.

        Args:
            category: Optional filter by category.

        Returns:
            List of provider definitions.
        """
        if category:
            return [p for p in self._provider_definitions.values() if p.category == category]
        return list(self._provider_definitions.values())

    async def get_effective_config(
        self,
        category: str,
        account_id: str,
        provider_name: str,
        repository: ConfigurationRepository,
    ) -> Optional[Dict[str, Any]]:
        """Resolve effective configuration (account override -> system default).

        Args:
            category: Configuration category.
            account_id: Account ID to check for overrides.
            provider_name: Provider identifier.
            repository: Configuration repository.

        Returns:
            Decrypted configuration dictionary if found, None otherwise.
        """
        cache_key = f"{category}:{account_id}:{provider_name}"
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.expires_at > now:
                return cached.config

        # Try account-level override first
        config_model = await repository.get_config(
            category=category,
            account_id=account_id,
            provider_name=provider_name,
            is_system=False,
        )

        # Fall back to system default if not found or disabled
        if not config_model or not config_model.enabled:
            config_model = await repository.get_config(
                category=category,
                account_id=self.SYSTEM_ACCOUNT_ID,
                provider_name=provider_name,
                is_system=True,
            )

        effective_config = None
        if config_model and config_model.enabled:
            # Decrypted config values are returned to the caller
            effective_config = self.encryption_service.decrypt_dict(config_model.config)

        # Update cache
        self._cache[cache_key] = CachedConfig(
            config=effective_config,
            expires_at=now + self.CACHE_TTL,
        )

        return effective_config

    async def get_system_configs(
        self, category: str, repository: ConfigurationRepository
    ) -> Sequence[ConfigurationModel]:
        """Get all configurations at the system level.

        Args:
            category: Filter by category.
            repository: Configuration repository.

        Returns:
            List of system-level configuration models.
        """
        return await repository.list_configs(
            category=category,
            account_id=self.SYSTEM_ACCOUNT_ID,
            is_system=True,
        )

    async def get_account_configs(
        self,
        category: str,
        account_id: str,
        repository: ConfigurationRepository,
    ) -> Sequence[ConfigurationModel]:
        """Get all configurations at the account level.

        Args:
            category: Filter by category.
            account_id: Account ID.
            repository: Configuration repository.

        Returns:
            List of account-level configuration models.
        """
        return await repository.list_configs(
            category=category,
            account_id=account_id,
            is_system=False,
        )

    async def create_config(
        self,
        account_id: str,
        category: str,
        provider_name: str,
        display_name: str,
        config: Dict[str, Any],
        logo_url: Optional[str] = None,
        enabled: bool = True,
        is_builtin: bool = False,
        is_system: bool = False,
        priority: int = 0,
        repository: Optional[ConfigurationRepository] = None,
    ) -> ConfigurationModel:
        """Create a new configuration record.

        Args:
            account_id: Account ID.
            category: Configuration category.
            provider_name: Provider identifier.
            display_name: Human-readable name.
            config: Configuration values (unencrypted).
            logo_url: Optional path to logo.
            enabled: Whether it's enabled.
            is_builtin: Whether it's built-in.
            is_system: Whether it's system-level.
            priority: Display priority.
            repository: Optional repository. Required if persisting.

        Returns:
            Created configuration model.
        """
        # Encrypt configuration values before storage
        encrypted_config = self.encryption_service.encrypt_dict(config)

        # Retrieve schema from provider definition if registered
        provider_def = self.get_provider_definition(category, provider_name)
        config_schema = provider_def.config_schema if provider_def else None

        new_config = ConfigurationModel(
            id=str(uuid.uuid4()),
            account_id=account_id,
            category=category,
            provider_name=provider_name,
            display_name=display_name,
            logo_url=logo_url,
            config_schema=config_schema,
            config=encrypted_config,
            enabled=enabled,
            is_builtin=is_builtin,
            is_system=is_system,
            priority=priority,
        )

        if repository:
            created_model = await repository.create(new_config)
        else:
            created_model = new_config

        # Invalidate cache for this configuration
        self._invalidate_cache(category, account_id, provider_name)

        return created_model

    async def update_config(
        self,
        config_id: str,
        config: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        enabled: Optional[bool] = None,
        priority: Optional[int] = None,
        repository: Optional[ConfigurationRepository] = None,
    ) -> Optional[ConfigurationModel]:
        """Update an existing configuration record.

        Args:
            config_id: ID of the configuration to update.
            config: New configuration values (unencrypted).
            display_name: New human-readable name.
            logo_url: New logo URL.
            enabled: New enabled status.
            priority: New priority.
            repository: Optional repository. Required if persisting.

        Returns:
            Updated configuration model if found, None otherwise.
        """
        if not repository:
            raise ValueError("Repository is required for update_config")

        config_model = await repository.get_by_id(config_id)
        if not config_model:
            return None

        if config is not None:
            config_model.config = self.encryption_service.encrypt_dict(config)
        if display_name is not None:
            config_model.display_name = display_name
        if logo_url is not None:
            config_model.logo_url = logo_url
        if enabled is not None:
            config_model.enabled = enabled
        if priority is not None:
            config_model.priority = priority

        updated_model = await repository.update(config_model)

        # Invalidate cache for this configuration
        self._invalidate_cache(
            config_model.category,
            config_model.account_id,
            config_model.provider_name,
        )

        return updated_model

    async def delete_config(
        self, config_id: str, repository: ConfigurationRepository
    ) -> bool:
        """Delete a configuration record.

        Args:
            config_id: ID of the configuration to delete.
            repository: Configuration repository.

        Returns:
            True if deleted successfully, False if not found.

        Raises:
            ValueError: If attempting to delete a built-in configuration.
        """
        config_model = await repository.get_by_id(config_id)
        if not config_model:
            return False

        if config_model.is_builtin:
            raise ValueError("Built-in configurations cannot be deleted")

        category = config_model.category
        account_id = config_model.account_id
        provider_name = config_model.provider_name

        result = await repository.delete(config_id)
        if result:
            self._invalidate_cache(category, account_id, provider_name)

        return result

    def _invalidate_cache(self, category: str, account_id: str, provider_name: str) -> None:
        """Invalidate the cache entry for a configuration.

        Args:
            category: Configuration category.
            account_id: Account ID.
            provider_name: Provider identifier.
        """
        cache_key = f"{category}:{account_id}:{provider_name}"
        if cache_key in self._cache:
            del self._cache[cache_key]
