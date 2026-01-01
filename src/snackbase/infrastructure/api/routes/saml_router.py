"""SAML authentication API routes.

Provides endpoints for SAML 2.0 Single Sign-On (SSO) flows.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.configuration.providers.saml import (
    AzureADSAMLProvider,
    GenericSAMLProvider,
    OktaSAMLProvider,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.repositories import AccountRepository

logger = get_logger(__name__)

router = APIRouter()

# Mapping of provider names to handler instances
SAML_HANDLERS = {
    "okta": OktaSAMLProvider(),
    "azure_ad": AzureADSAMLProvider(),
    "generic_saml": GenericSAMLProvider(),
}


@router.get(
    "/sso",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirects to Identity Provider"},
        404: {"description": "Account or provider not found"},
    },
)
async def sso(
    request: Request,
    account: str = Query(..., description="Account slug or ID"),
    provider: Optional[str] = Query(None, description="Specific provider name to force use of"),
    relay_state: Optional[str] = Query(None, description="Client state to preserve"),
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """Initiate SAML Single Sign-On flow.

    Redirects the user to the Identity Provider's SSO URL with a SAML AuthnRequest.

    Args:
        request: FastAPI request object.
        account: Account identifier (slug or ID).
        provider: Optional provider name to use (e.g., 'okta', 'azure_ad').
                  If not specified, uses the configured provider for the account.
        relay_state: Optional state to return after successful authentication.
        session: Database session.

    Returns:
        RedirectResponse to the IdP.
    """
    config_registry = getattr(request.app.state, "config_registry", None)
    if not config_registry:
        logger.error("Configuration registry not found in app state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System configuration error",
        )

    # 1. Resolve account
    account_repo = AccountRepository(session)
    account_model = await account_repo.get_by_slug_or_code(account)
    if not account_model:
        logger.info("SAML SSO failed: account not found", account=account)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account}' not found",
        )
    account_id = account_model.id

    # 2. Determine provider and get configuration
    selected_provider_name = provider
    config_dict = None

    if selected_provider_name:
        # User specified a provider
        config_dict = await config_registry.get_effective_config(
            category="saml_providers",
            provider_name=selected_provider_name,
            account_id=account_id,
        )
        if not config_dict:
            logger.info(
                "SAML SSO failed: requested provider not configured",
                provider=selected_provider_name,
                account_id=account_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SAML provider '{selected_provider_name}' not configured for this account",
            )
    else:
        # Determine provider automatically
        # List all available SAML providers for this account
        # We need to check each one to see if it's enabled for this account
        # Since get_effective_config handles hierarchy, we can check known providers
        # or use get_account_configs if available (but that only gives account level overrides)
        
        # Strategy: Iterate through supported SAML providers and find the first enabled one
        # This assumes single SAML provider per account is the common case, or arbitrary priority
        # A better approach in ConfigRegistry would be "get_active_providers(category, account_id)"
        # For now, we iterate.
        found_config = None
        for name in SAML_HANDLERS.keys():
             conf = await config_registry.get_effective_config(
                category="saml_providers",
                provider_name=name,
                account_id=account_id,
            )
             if conf:
                 found_config = conf
                 selected_provider_name = name
                 break
        
        if found_config:
            config_dict = found_config
        else:
            logger.info("SAML SSO failed: no active SAML provider found", account_id=account_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active SAML provider configured for this account",
            )

    # 3. Get provider handler
    handler = SAML_HANDLERS.get(selected_provider_name)
    if not handler:
        logger.error(
            "SAML SSO failed: handler not found for provider",
            provider=selected_provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Handler for provider '{selected_provider_name}' not found",
        )

    # 4. Generate authorization URL
    from snackbase.core.config import get_settings
    settings = get_settings()
    
    # ACS URL where IdP should post response
    acs_url = f"{settings.external_url.rstrip('/')}{settings.api_prefix}/auth/saml/acs"
    
    try:
        auth_url = await handler.get_authorization_url(
            config=config_dict,
            redirect_uri=acs_url,
            relay_state=relay_state,
        )
    except Exception as e:
        logger.error(
            "SAML SSO failed: error generating auth URL",
            provider=selected_provider_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating SAML request: {str(e)}",
        )

    logger.info(
        "SAML SSO initiated",
        account_id=account_id,
        provider=selected_provider_name,
        relay_state=relay_state,
    )

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
