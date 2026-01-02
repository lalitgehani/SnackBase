from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
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


@router.get("/configuration/providers")
async def get_available_providers(
    _admin: SuperadminUser,
    request: Request,
    category: Optional[str] = None,
):
    """List all available provider definitions."""
    try:
        registry = request.app.state.config_registry
        providers = registry.list_provider_definitions(category)
        return [
            {
                "category": p.category,
                "name": p.name,
                "display_name": p.display_name,
                "logo_url": p.logo_url,
                "is_builtin": p.is_builtin,
            }
            for p in providers
        ]
    except Exception as e:
        logger.error("Failed to fetch available providers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available providers",
        )


@router.get("/configuration/schema/{category}/{provider_name}")
async def get_provider_schema(
    _admin: SuperadminUser,
    request: Request,
    category: str,
    provider_name: str,
):
    """Get the JSON schema for a specific provider."""
    try:
        registry = request.app.state.config_registry
        p_def = registry.get_provider_definition(category, provider_name)
        if not p_def:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return p_def.config_schema
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch provider schema", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch provider schema",
        )


@router.get("/configuration/{config_id}/values")
async def get_configuration_values(
    _admin: SuperadminUser,
    config_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Get decrypted configuration values with secrets masked."""
    try:
        repo = ConfigurationRepository(db)
        config_model = await repo.get_by_id(config_id)
        if not config_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

        registry = request.app.state.config_registry
        values = registry.encryption_service.decrypt_dict(config_model.config)

        # Mask secrets if schema is available
        p_def = registry.get_provider_definition(config_model.category, config_model.provider_name)
        if p_def and p_def.config_schema:
            properties = p_def.config_schema.get("properties", {})
            for key, prop in properties.items():
                if prop.get("writeOnly") or prop.get("format") == "password" or "secret" in key.lower():
                    if key in values and values[key]:
                        values[key] = "••••••••"

        return values
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch configuration values", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configuration values",
        )


@router.patch("/configuration/{config_id}/values")
async def update_configuration_values(
    _admin: SuperadminUser,
    config_id: str,
    request: Request,
    values: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Update configuration values."""
    try:
        repo = ConfigurationRepository(db)
        config_model = await repo.get_by_id(config_id)
        if not config_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

        registry = request.app.state.config_registry
        
        # Merge values, preserving masked secrets if not updated
        current_values = registry.encryption_service.decrypt_dict(config_model.config)
        new_values = {}
        for key, val in values.items():
            if val == "••••••••" and key in current_values:
                new_values[key] = current_values[key]
            else:
                new_values[key] = val

        # Handle other fields that might be passed (display_name, logo_url, etc)
        # For now, focus on the 'config' field
        config_model.config = registry.encryption_service.encrypt_dict(new_values)
        await repo.update(config_model)
        await db.commit()

        # Invalidate cache
        registry._invalidate_cache(config_model.category, config_model.account_id, config_model.provider_name)

        return {"status": "success"}
    except Exception as e:
        logger.error("Failed to update configuration values", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration values",
        )


@router.post("/configuration")
async def create_configuration(
    _admin: SuperadminUser,
    request: Request,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new configuration record."""
    try:
        registry = request.app.state.config_registry
        
        # Validate required fields in data
        required = ["category", "provider_name", "display_name", "config"]
        for field in required:
            if field not in data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing field: {field}")

        # Account ID defaults to system account if not provided
        account_id = data.get("account_id", registry.SYSTEM_ACCOUNT_ID)
        is_system = account_id == registry.SYSTEM_ACCOUNT_ID

        new_config = await registry.create_config(
            account_id=account_id,
            category=data["category"],
            provider_name=data["provider_name"],
            display_name=data["display_name"],
            config=data["config"],
            logo_url=data.get("logo_url"),
            enabled=data.get("enabled", True),
            is_builtin=False,  # Custom configs are never built-in
            is_system=is_system,
            priority=data.get("priority", 0),
        )

        return {
            "id": new_config.id,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration",
        )


@router.post("/configuration/test-connection")
async def test_provider_connection(
    _admin: SuperadminUser,
    request: Request,
    data: Dict[str, Any] = Body(...),
):
    """Test connection for a provider configuration."""
    try:
        category = data.get("category")
        provider_name = data.get("provider_name")
        config_values = data.get("config")

        if not category or not provider_name or config_values is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields")

        # Resolve provider handler
        # We need a way to get the handler instance. 
        # For now, let's look at how providers are handled in auth_router or similar.
        # Most handlers are registered in the registry but the registry only stores definitions.
        # We might need a ProviderFactory or similar.
        
        # For OAuth/SAML, we have handlers.
        from snackbase.infrastructure.configuration.providers.oauth import (
            GoogleOAuthHandler, GitHubOAuthHandler, MicrosoftOAuthHandler, AppleOAuthHandler
        )
        from snackbase.infrastructure.configuration.providers.saml import (
            OktaSAMLProvider, AzureADSAMLProvider, GenericSAMLProvider
        )
        
        handlers = {
            "google": GoogleOAuthHandler,
            "github": GitHubOAuthHandler,
            "microsoft": MicrosoftOAuthHandler,
            "apple": AppleOAuthHandler,
            "okta": OktaSAMLProvider,
            "azure_ad": AzureADSAMLProvider,
            "generic_saml": GenericSAMLProvider,
        }
        
        handler_class = handlers.get(provider_name)
        if not handler_class:
            return {"success": False, "message": f"Provider {provider_name} does not support connection testing yet."}
            
        handler = handler_class()
        
        # Check if test_connection exists and call it
        if hasattr(handler, "test_connection"):
            success, message = await handler.test_connection(config_values)
            return {"success": success, "message": message}
        else:
            return {"success": False, "message": f"Provider {provider_name} does not implement test_connection."}

    except Exception as e:
        logger.error("Connection test failed", error=str(e))
        return {"success": False, "message": f"Internal error during test: {str(e)}"}
