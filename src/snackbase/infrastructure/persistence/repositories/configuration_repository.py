"""Configuration repository for database operations."""

from typing import List, Optional, Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel


class ConfigurationRepository:
    """Repository for configuration database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(self, config: ConfigurationModel) -> ConfigurationModel:
        """Create a new configuration.

        Args:
            config: Configuration model to create.

        Returns:
            Created configuration model.
        """
        self.session.add(config)
        await self.session.flush()
        return config

    async def get_by_id(self, config_id: str) -> Optional[ConfigurationModel]:
        """Get a configuration by ID.

        Args:
            config_id: Configuration ID (UUID).

        Returns:
            Configuration model if found, None otherwise.
        """
        result = await self.session.execute(
            select(ConfigurationModel).where(ConfigurationModel.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_config(
        self,
        category: str,
        account_id: str,
        provider_name: str,
        is_system: bool = False,
    ) -> Optional[ConfigurationModel]:
        """Get a configuration by unique keys.

        Args:
            category: Configuration category.
            account_id: Account ID.
            provider_name: Provider identifier.
            is_system: Whether to look for system-level config.

        Returns:
            Configuration model if found, None otherwise.
        """
        query = select(ConfigurationModel).where(
            and_(
                ConfigurationModel.category == category,
                ConfigurationModel.account_id == account_id,
                ConfigurationModel.provider_name == provider_name,
                ConfigurationModel.is_system == is_system,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_configs(
        self,
        category: Optional[str] = None,
        account_id: Optional[str] = None,
        is_system: Optional[bool] = None,
        enabled_only: bool = False,
    ) -> Sequence[ConfigurationModel]:
        """List configurations with optional filters.

        Args:
            category: Filter by category.
            account_id: Filter by account ID.
            is_system: Filter by system flag.
            enabled_only: Whether to return only enabled configurations.

        Returns:
            List of configuration models.
        """
        query = select(ConfigurationModel)

        filters = []
        if category:
            filters.append(ConfigurationModel.category == category)
        if account_id:
            filters.append(ConfigurationModel.account_id == account_id)
        if is_system is not None:
            filters.append(ConfigurationModel.is_system == is_system)
        if enabled_only:
            filters.append(ConfigurationModel.enabled == True)  # noqa: E712

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(ConfigurationModel.priority.asc(), ConfigurationModel.created_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, config: ConfigurationModel) -> ConfigurationModel:
        """Update an existing configuration.

        Args:
            config: Configuration model with updated fields.

        Returns:
            Updated configuration model.
        """
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def get_default_config(
        self,
        category: str,
        account_id: str,
        is_system: bool = False,
    ) -> Optional[ConfigurationModel]:
        """Get the default configuration for a category and account scope.

        Args:
            category: Configuration category (e.g., 'auth_providers').
            account_id: Account ID to check.
            is_system: Whether to look at system-level configs.

        Returns:
            The default configuration model if one is set, None otherwise.
        """
        query = select(ConfigurationModel).where(
            and_(
                ConfigurationModel.category == category,
                ConfigurationModel.account_id == account_id,
                ConfigurationModel.is_system == is_system,
                ConfigurationModel.is_default == True,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_default_config(
        self,
        config_id: str,
        category: str,
        account_id: str,
        is_system: bool,
    ) -> Optional[ConfigurationModel]:
        """Set a configuration as the default for its category and account scope.

        Atomically clears any existing default in the same (category, account_id, is_system)
        scope before setting the new default. Enforces the single-default invariant.

        Args:
            config_id: ID of the configuration to make default.
            category: Configuration category.
            account_id: Account ID scope.
            is_system: Whether this is system-level scope.

        Returns:
            The updated configuration model, or None if not found.

        Raises:
            ValueError: If the target config is disabled.
        """
        # Clear existing default in this scope
        await self.session.execute(
            update(ConfigurationModel)
            .where(
                and_(
                    ConfigurationModel.category == category,
                    ConfigurationModel.account_id == account_id,
                    ConfigurationModel.is_system == is_system,
                    ConfigurationModel.is_default == True,  # noqa: E712
                )
            )
            .values(is_default=False)
        )

        target = await self.get_by_id(config_id)
        if not target:
            return None

        if not target.enabled:
            raise ValueError(
                f"Cannot set disabled provider '{target.provider_name}' as default. "
                "Enable it first."
            )

        target.is_default = True
        await self.session.flush()
        await self.session.refresh(target)
        return target

    async def unset_default_config(self, config_id: str) -> bool:
        """Clear the default flag on a specific configuration.

        Args:
            config_id: ID of the configuration to clear default from.

        Returns:
            True if the config was found and updated, False otherwise.
        """
        config = await self.get_by_id(config_id)
        if not config:
            return False
        config.is_default = False
        await self.session.flush()
        return True

    async def delete(self, config_id: str) -> bool:
        """Delete a configuration by ID.

        Args:
            config_id: Configuration ID.

        Returns:
            True if deleted, False if not found.
        """
        config = await self.get_by_id(config_id)
        if not config:
            return False

        await self.session.delete(config)
        await self.session.flush()
        return True
