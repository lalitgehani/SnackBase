from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.persistence.repositories.configuration_repository import ConfigurationRepository
from snackbase.core.logging import get_logger

router = APIRouter(tags=["admin"])
logger = get_logger(__name__)

@router.get("/configuration/stats")
async def get_configuration_stats(
    db: AsyncSession = Depends(get_db_session),
    # TODO: Add superadmin dependency check here
):
    """Get configuration statistics for the dashboard.
    
    Returns counts of enabled system and account configurations grouped by category.
    """
    try:
        # System configs count by category
        system_query = select(
            ConfigurationModel.category,
            func.count(ConfigurationModel.id)
        ).where(
            and_(
                ConfigurationModel.is_system == True,
                ConfigurationModel.enabled == True
            )
        ).group_by(ConfigurationModel.category)
        
        system_result = await db.execute(system_query)
        system_stats = {row[0]: row[1] for row in system_result.all()}
        
        # Account configs count by category
        account_query = select(
            ConfigurationModel.category,
            func.count(ConfigurationModel.id)
        ).where(
            and_(
                ConfigurationModel.is_system == False,
                ConfigurationModel.enabled == True
            )
        ).group_by(ConfigurationModel.category)
        
        account_result = await db.execute(account_query)
        account_stats = {row[0]: row[1] for row in account_result.all()}
        
        # Calculate totals
        total_system = sum(system_stats.values())
        total_account = sum(account_stats.values())
        
        return {
            "system_configs": {
                "total": total_system,
                "by_category": system_stats
            },
            "account_configs": {
                "total": total_account,
                "by_category": account_stats
            }
        }
    except Exception as e:
        logger.error("Failed to fetch configuration stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configuration statistics"
        )

@router.get("/configuration/recent")
async def get_recent_configurations(
    limit: int = 5,
    db: AsyncSession = Depends(get_db_session),
    # TODO: Add superadmin dependency check here
):
    """Get recently modified configurations.
    
    Args:
        limit: Number of records to return (default: 5)
    """
    try:
        # Fetch recently updated configs
        query = select(ConfigurationModel).order_by(
            desc(ConfigurationModel.updated_at)
        ).limit(limit)
        
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
                "logo_url": config.logo_url
            }
            for config in configs
        ]
    except Exception as e:
        logger.error("Failed to fetch recent configurations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent configurations"
        )
