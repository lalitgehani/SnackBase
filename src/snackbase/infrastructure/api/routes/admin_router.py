from typing import Any

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


def _validate_backup_settings_values(category: str, values: dict[str, Any]) -> None:
    """Reject invalid backup settings on the configuration write path.

    Raises:
        HTTPException: 400 carrying the parser's message when a value is invalid.
    """
    if category != "backup_settings":
        return
    from snackbase.infrastructure.configuration.providers.backup.backup_settings import (
        validate_backup_settings,
    )

    try:
        validate_backup_settings(values)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
            .where(and_(ConfigurationModel.is_system.is_(False), ConfigurationModel.enabled))
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
                "is_default": config.is_default,
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
            and_(ConfigurationModel.is_system.is_(False), ConfigurationModel.account_id == account_id)
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
                "is_default": config.is_default,
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
    request: Request,
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

        if config.category == "storage_providers" and not config.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        config.enabled = enabled

        # Automatically clear is_default when disabling a provider
        if not enabled and config.is_default:
            config.is_default = False
            logger.info(
                "Cleared default flag from disabled provider",
                provider=config.provider_name,
                category=config.category,
                account_id=config.account_id,
            )

        await repo.update(config)
        await db.commit()

        # Invalidate cache
        registry = request.app.state.config_registry
        registry._invalidate_cache(config.category, config.account_id, config.provider_name)

        return {"status": "success", "enabled": config.enabled, "is_default": config.is_default}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration",
        )


@router.post("/configuration/{config_id}/set-default")
async def set_configuration_default(
    _admin: SuperadminUser,
    config_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Set a configuration as the default for its category and account scope.

    Atomically clears any existing default in the same scope before setting this one.
    Only enabled providers can be set as default.
    """
    try:
        repo = ConfigurationRepository(db)
        config = await repo.get_by_id(config_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )

        if not config.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set a disabled provider as default. Enable it first.",
            )

        if config.category == "storage_providers" and not config.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        updated = await repo.set_default_config(
            config_id=config_id,
            category=config.category,
            account_id=config.account_id,
            is_system=config.is_system,
        )
        await db.commit()

        # Invalidate cache for the affected provider
        registry = request.app.state.config_registry
        registry._invalidate_cache(config.category, config.account_id, config.provider_name)

        return {
            "status": "success",
            "is_default": True,
            "provider_name": updated.provider_name,
            "display_name": updated.display_name,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to set default configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set default configuration",
        )


@router.delete("/configuration/{config_id}/set-default")
async def unset_configuration_default(
    _admin: SuperadminUser,
    config_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Clear the default flag from a configuration without setting a new default."""
    try:
        repo = ConfigurationRepository(db)
        config = await repo.get_by_id(config_id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )

        if config.category == "storage_providers" and not config.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        await repo.unset_default_config(config_id)
        await db.commit()

        # Invalidate cache for the affected provider
        registry = request.app.state.config_registry
        registry._invalidate_cache(config.category, config.account_id, config.provider_name)

        return {"status": "success", "is_default": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to unset default configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unset default configuration",
        )


@router.delete("/configuration/{config_id}")
async def delete_configuration(
    _admin: SuperadminUser,
    config_id: str,
    request: Request,
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

        # Invalidate cache
        registry = request.app.state.config_registry
        registry._invalidate_cache(config.category, config.account_id, config.provider_name)

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
    category: str | None = None,
):
    """List all available provider definitions."""
    try:
        registry = request.app.state.config_registry
        providers = registry.list_provider_definitions(category)
        return [
            {
                "category": p.category,
                "provider_name": p.provider_name,
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

        if config_model.category == "storage_providers" and not config_model.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        registry = request.app.state.config_registry
        schema = config_model.config_schema
        if schema is None:
            p_def = registry.get_provider_definition(
                config_model.category, config_model.provider_name
            )
            schema = p_def.config_schema if p_def else None
        values = registry._decrypt_config(
            config_model.config,
            schema,
            category=config_model.category,
            provider_name=config_model.provider_name,
        )

        # Mask schema-declared secrets (and legacy writeOnly/password heuristics)
        from snackbase.infrastructure.security.encryption import (
            REDACTION_PLACEHOLDER,
            extract_secret_paths_from_schema,
        )
        from snackbase.infrastructure.security.redaction import redact_config_secrets

        secret_paths = extract_secret_paths_from_schema(schema)
        if secret_paths:
            values = redact_config_secrets(values, secret_paths)
        elif schema and isinstance(schema.get("properties"), dict):
            for key, prop in schema["properties"].items():
                if not isinstance(prop, dict):
                    continue
                if (
                    prop.get("writeOnly")
                    or prop.get("format") == "password"
                    or "secret" in key.lower()
                ):
                    if key in values and values[key]:
                        values[key] = REDACTION_PLACEHOLDER

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
    values: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Update configuration values."""
    try:
        repo = ConfigurationRepository(db)
        config_model = await repo.get_by_id(config_id)
        if not config_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

        if config_model.category == "storage_providers" and not config_model.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        registry = request.app.state.config_registry
        schema = config_model.config_schema
        if schema is None:
            p_def = registry.get_provider_definition(
                config_model.category, config_model.provider_name
            )
            schema = p_def.config_schema if p_def else None

        # Merge values, preserving masked secrets if not updated
        from snackbase.infrastructure.security.encryption import REDACTION_PLACEHOLDER

        current_values = registry._decrypt_config(
            config_model.config,
            schema,
            category=config_model.category,
            provider_name=config_model.provider_name,
        )
        new_values = {}
        for key, val in values.items():
            if val == REDACTION_PLACEHOLDER and key in current_values:
                new_values[key] = current_values[key]
            else:
                new_values[key] = val

        merged_values = dict(current_values)
        merged_values.update(new_values)
        _validate_backup_settings_values(config_model.category, merged_values)

        config_model.config = registry._encrypt_config(new_values, schema)
        await repo.update(config_model)
        await db.commit()

        # Invalidate cache
        registry._invalidate_cache(
            config_model.category, config_model.account_id, config_model.provider_name
        )

        return {"status": "success"}
    except HTTPException:
        raise
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
    data: dict[str, Any] = Body(...),
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

        if data["category"] == "storage_providers" and not is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage providers can only be configured at system level.",
            )

        # Custom providers may supply config_schema with secret: true markers
        config_schema = data.get("config_schema")
        provider_def = registry.get_provider_definition(
            data["category"], data["provider_name"]
        )
        _validate_backup_settings_values(data["category"], data.get("config") or {})
        if provider_def is None and config_schema is None:
            # Reject credential-like custom configs without a schema
            config_keys = set((data.get("config") or {}).keys())
            credential_hints = {
                "password",
                "secret",
                "token",
                "api_key",
                "client_secret",
                "access_key",
                "private_key",
            }
            if any(
                any(h in k.lower() for h in credential_hints) for k in config_keys
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "config_schema with secret: true markers is required for "
                        "custom providers that store credentials"
                    ),
                )

        repo = ConfigurationRepository(db)
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
            repository=repo,
            config_schema=config_schema,
        )

        await db.commit()

        return {
            "id": new_config.id,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        # Handle unique constraint violation (IntegrityError)
        # Note: We import IntegrityError locally to avoid top-level SQLAlchemy dependency if possible,
        # or use string matching if the exception type varies.
        # But importing it is cleaner.
        from sqlalchemy.exc import IntegrityError

        if isinstance(e, IntegrityError) or "UNIQUE constraint failed" in str(e):
            logger.info("Configuration creation failed: duplicate exists", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Configuration already exists for this provider and category.",
            )

        logger.error("Failed to create configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration",
        )


@router.post("/configuration/test-connection")
async def test_provider_connection(
    _admin: SuperadminUser,
    request: Request,
    data: dict[str, Any] = Body(...),
):
    """Test connection for a provider configuration."""
    try:
        import asyncio
        category = data.get("category")
        provider_name = data.get("provider_name")
        config_values = data.get("config")

        if not category or not provider_name or config_values is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields")

        # Resolve provider handler
        # Note: In a larger system, this could be moved to a ProviderFactory
        from snackbase.infrastructure.configuration.providers.oauth import (
            AppleOAuthHandler,
            GitHubOAuthHandler,
            GoogleOAuthHandler,
            MicrosoftOAuthHandler,
        )
        from snackbase.infrastructure.configuration.providers.saml import (
            AzureADSAMLProvider,
            GenericSAMLProvider,
            OktaSAMLProvider,
        )
        from snackbase.infrastructure.services.email.aws_ses_provider import (
            AWSESProvider,
            AWSESSettings,
        )
        from snackbase.infrastructure.services.email.resend_provider import (
            ResendProvider,
            ResendSettings,
        )
        from snackbase.infrastructure.services.email.smtp_provider import (
            SMTPProvider,
            SMTPSettings,
        )
        from snackbase.infrastructure.storage.local_storage_provider import (
            LocalStorageProvider,
        )
        from snackbase.infrastructure.storage.s3_storage_provider import (
            S3StorageProvider,
            S3StorageSettings,
        )

        # Handle storage providers
        if category == "storage_providers":
            if provider_name == "local":
                try:
                    local_provider = LocalStorageProvider()
                    success, message = await asyncio.wait_for(
                        local_provider.test_connection(),
                        timeout=10.0
                    )
                    return {"success": success, "message": message or "Local storage is available"}
                except TimeoutError:
                    return {
                        "success": False,
                        "message": "Local storage connection test timed out after 10 seconds.",
                    }
                except Exception as e:
                    return {"success": False, "message": f"Local storage test failed: {str(e)}"}

            elif provider_name == "s3":
                try:
                    s3_settings = S3StorageSettings(**config_values)
                    s3_provider = S3StorageProvider(s3_settings)
                    success, message = await asyncio.wait_for(
                        s3_provider.test_connection(),
                        timeout=10.0
                    )
                    return {"success": success, "message": message or "S3 connection successful"}
                except TimeoutError:
                    return {
                        "success": False,
                        "message": (
                            "Connection test timed out after 10 seconds. "
                            "Check your network or AWS credentials."
                        ),
                    }
                except Exception as e:
                    return {"success": False, "message": f"S3 storage test failed: {str(e)}"}

        # Handle email providers
        if category == "email_providers":
            if provider_name == "smtp":
                try:
                    smtp_settings = SMTPSettings(**config_values)
                    smtp_provider = SMTPProvider(smtp_settings)
                    success, message = await asyncio.wait_for(
                        smtp_provider.test_connection(),
                        timeout=10.0
                    )
                    return {"success": success, "message": message or "SMTP connection successful"}
                except TimeoutError:
                    return {
                        "success": False,
                        "message": (
                            "Connection test timed out after 10 seconds. "
                            "Check your network or SMTP server settings."
                        ),
                    }
                except Exception as e:
                    return {"success": False, "message": f"SMTP test failed: {str(e)}"}

            elif provider_name == "aws_ses":
                try:
                    ses_settings = AWSESSettings(**config_values)
                    ses_provider = AWSESProvider(ses_settings)
                    success, message = await asyncio.wait_for(
                        ses_provider.test_connection(),
                        timeout=10.0
                    )
                    return {"success": success, "message": message or "AWS SES connection successful"}
                except TimeoutError:
                    return {
                        "success": False,
                        "message": (
                            "Connection test timed out after 10 seconds. "
                            "Check your network or AWS credentials."
                        ),
                    }
                except Exception as e:
                    return {"success": False, "message": f"AWS SES test failed: {str(e)}"}

            elif provider_name == "resend":
                try:
                    resend_settings = ResendSettings(**config_values)
                    resend_provider = ResendProvider(resend_settings)
                    success, message = await asyncio.wait_for(
                        resend_provider.test_connection(),
                        timeout=10.0
                    )
                    return {"success": success, "message": message or "Resend connection successful"}
                except TimeoutError:
                    return {
                        "success": False,
                        "message": (
                            "Connection test timed out after 10 seconds. "
                            "Check your network or API key."
                        ),
                    }
                except Exception as e:
                    return {"success": False, "message": f"Resend test failed: {str(e)}"}

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
            return {
                "success": False,
                "message": f"Provider {provider_name} does not support connection testing yet."
            }

        handler = handler_class()

        # Execute test with 10-second timeout
        try:
            success, message = await asyncio.wait_for(
                handler.test_connection(config_values),
                timeout=10.0
            )
            return {"success": success, "message": message}
        except TimeoutError:
            return {
                "success": False,
                "message": "Connection test timed out after 10 seconds. Check your network or provider settings."
            }
        except Exception as e:
            return {"success": False, "message": f"Test execution failed: {str(e)}"}

    except Exception as e:
        logger.error("Connection test endpoint failed", error=str(e))
        return {"success": False, "message": f"Internal server error: {str(e)}"}
