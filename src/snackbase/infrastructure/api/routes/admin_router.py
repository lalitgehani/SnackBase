from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)

router = APIRouter(tags=["admin"])
logger = get_logger(__name__)


@router.get("/configuration/stats")
async def get_configuration_stats(
    _admin: SuperadminUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Get configuration statistics for the dashboard.

    Returns counts of enabled system and account configurations grouped by category.
    """
    try:
        # System configs count by category
        system_query = (
            select(ConfigurationModel.category, func.count(ConfigurationModel.id))
            .where(and_(ConfigurationModel.is_system, ConfigurationModel.enabled))
            .group_by(ConfigurationModel.category)
        )

        system_result = await db.execute(system_query)
        system_stats = {row[0]: row[1] for row in system_result.all()}

        # Account configs count by category
        account_query = (
            select(ConfigurationModel.category, func.count(ConfigurationModel.id))
            .where(and_(ConfigurationModel.is_system == False, ConfigurationModel.enabled))
            .group_by(ConfigurationModel.category)
        )

        account_result = await db.execute(account_query)
        account_stats = {row[0]: row[1] for row in account_result.all()}

        # Calculate totals
        total_system = sum(system_stats.values())
        total_account = sum(account_stats.values())

        return {
            "system_configs": {"total": total_system, "by_category": system_stats},
            "account_configs": {"total": total_account, "by_category": account_stats},
        }
    except Exception as e:
        logger.error("Failed to fetch configuration stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configuration statistics",
        )


@router.get("/configuration/recent")
async def get_recent_configurations(
    _admin: SuperadminUser,
    limit: int = 5,
    db: AsyncSession = Depends(get_db_session),
):
    """Get recently modified configurations.

    Args:
        limit: Number of records to return (default: 5)
    """
    try:
        # Fetch recently updated configs
        query = (
            select(ConfigurationModel).order_by(desc(ConfigurationModel.updated_at)).limit(limit)
        )

        result = await db.execute(query)
        configs = result.scalars().all()

        return [
            {
                "id": config.id,
                "display_name": config.display_name,
                "provider_name": config.provider_name,
                "category": config.category,
                "updated_at": config.updated_at,
                "is_system": config.is_system,
                "account_id": config.account_id,
                "logo_url": config.logo_url,
            }
            for config in configs
        ]
    except Exception as e:
        logger.error("Failed to fetch recent configurations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent configurations",
        )


@router.get("/configuration/system")
async def get_system_configurations(
    _admin: SuperadminUser,
    category: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all system configurations.

    Args:
        category: Optional category filter.
    """
    try:
        query = select(ConfigurationModel).where(ConfigurationModel.is_system)

        if category:
            query = query.where(ConfigurationModel.category == category)

        query = query.order_by(
            ConfigurationModel.priority.asc(), ConfigurationModel.created_at.desc()
        )

        result = await db.execute(query)
        configs = result.scalars().all()

        return [
            {
                "id": config.id,
                "display_name": config.display_name,
                "provider_name": config.provider_name,
                "category": config.category,
                "enabled": config.enabled,
                "is_builtin": config.is_builtin,
                "priority": config.priority,
                "updated_at": config.updated_at,
                "logo_url": config.logo_url,
            }
            for config in configs
        ]
    except Exception as e:
        logger.error("Failed to fetch system configurations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system configurations",
        )


@router.get("/configuration/account")
async def get_account_configurations(
    _admin: SuperadminUser,
    account_id: str,
    category: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all configurations for a specific account.

    Args:
        account_id: Account ID to fetch configurations for.
        category: Optional category filter.
    """
    try:
        # Verify account exists by attempting to query it
        from snackbase.infrastructure.persistence.models.account import AccountModel

        account_query = select(AccountModel).where(AccountModel.id == account_id)
        account_result = await db.execute(account_query)
        account = account_result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        # Query account-level configurations
        query = select(ConfigurationModel).where(
            and_(ConfigurationModel.is_system == False, ConfigurationModel.account_id == account_id)
        )

        if category:
            query = query.where(ConfigurationModel.category == category)

        query = query.order_by(
            ConfigurationModel.priority.asc(), ConfigurationModel.created_at.desc()
        )

        result = await db.execute(query)
        configs = result.scalars().all()

        return [
            {
                "id": config.id,
                "display_name": config.display_name,
                "provider_name": config.provider_name,
                "category": config.category,
                "enabled": config.enabled,
                "priority": config.priority,
                "updated_at": config.updated_at,
                "logo_url": config.logo_url,
                "account_id": config.account_id,
            }
            for config in configs
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch account configurations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch account configurations",
        )


@router.patch("/configuration/{config_id}")
async def update_configuration_status(
    _admin: SuperadminUser,
    config_id: str,
    enabled: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
):
    """Update configuration status (enable/disable).

    Args:
        config_id: Configuration ID.
        enabled: New enabled status.
    """
    try:
        repo = ConfigurationRepository(db)
        config = await repo.get_by_id(config_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )

        config.enabled = enabled
        await repo.update(config)
        await db.commit()

        return {"status": "success", "enabled": config.enabled}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration",
        )


@router.delete("/configuration/{config_id}")
async def delete_configuration(
    _admin: SuperadminUser,
    config_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a configuration.

    Cannot delete built-in providers.
    """
    try:
        repo = ConfigurationRepository(db)
        config = await repo.get_by_id(config_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )

        if config.is_builtin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete built-in provider"
            )

        await repo.delete(config_id)
        await db.commit()

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration",
        )
