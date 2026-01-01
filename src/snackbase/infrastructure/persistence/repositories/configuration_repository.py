"""Configuration repository for database operations."""

from typing import List, Optional, Sequence

from sqlalchemy import and_, select
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
