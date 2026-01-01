"""OAuth authentication API routes.

Provides endpoints for OAuth 2.0 authorization flows.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.schemas.auth_schemas import (
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
)
from snackbase.infrastructure.configuration.providers.oauth import (
    AppleOAuthHandler,
    GitHubOAuthHandler,
    GoogleOAuthHandler,
    MicrosoftOAuthHandler,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    OAuthStateRepository,
)

logger = get_logger(__name__)

router = APIRouter()

# Mapping of provider names to handler instances
OAUTH_HANDLERS = {
    "google": GoogleOAuthHandler(),
    "github": GitHubOAuthHandler(),
    "microsoft": MicrosoftOAuthHandler(),
    "apple": AppleOAuthHandler(),
}


@router.post(
    "/{provider_name}/authorize",
    status_code=status.HTTP_200_OK,
    response_model=OAuthAuthorizeResponse,
    responses={
        400: {"description": "Validation error"},
        404: {"description": "Provider not configured or account not found"},
    },
)
async def authorize(
    provider_name: str,
    request_body: OAuthAuthorizeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> OAuthAuthorizeResponse:
    """Initiate OAuth authorization flow.

    Generates an authorization URL for the specified provider and stores
    the flow state in the database for CSRF protection.

    Flow:
    1. Resolve provider configuration (account override -> system fallback)
    2. Generate state token (if not provided)
    3. Store state in oauth_states table
    4. Generate authorization URL via provider handler
    5. Return URL and state
    """
    config_registry = getattr(request.app.state, "config_registry", None)
    if not config_registry:
        logger.error("Configuration registry not found in app state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System configuration error",
        )

    # 1. Resolve account (if provided)
    account_id = "00000000-0000-0000-0000-000000000000"  # Default to system level identifier
    if request_body.account:
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_slug_or_code(request_body.account)
        if not account:
            logger.info("OAuth authorize failed: account not found", account=request_body.account)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{request_body.account}' not found",
            )
        account_id = account.id

    # 2. Get provider configuration
    # get_effective_config handles hierarchical resolution and checks if enabled
    try:
        config_dict = await config_registry.get_effective_config(
            category="auth_providers",
            provider_name=provider_name,
            account_id=account_id,
        )
    except Exception as e:
        logger.error(
            "Error retrieving provider configuration",
            provider=provider_name,
            account_id=account_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving provider configuration",
        )

    if config_dict is None:
        logger.info(
            "OAuth authorize failed: provider not configured or disabled",
            provider=provider_name,
            account_id=account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not configured or disabled for this account",
        )

    # 3. Get provider handler
    handler = OAUTH_HANDLERS.get(provider_name)
    if not handler:
        logger.info("OAuth authorize failed: no handler for provider", provider=provider_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' handler not found",
        )

    # 4. Generate/Validate state token
    state_token = request_body.state or secrets.token_urlsafe(32)

    # 5. Store state in database
    oauth_state_repo = OAuthStateRepository(session)
    
    # Check if a state with this token already exists
    existing_state = await oauth_state_repo.get_by_token(state_token)
    if existing_state:
        if request_body.state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State token already in use",
            )
        state_token = secrets.token_urlsafe(32)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    state_model = OAuthStateModel(
        id=str(uuid.uuid4()),
        provider_name=provider_name,
        state_token=state_token,
        redirect_uri=request_body.redirect_uri,
        expires_at=expires_at,
        metadata_={"account_id": account_id},
    )
    
    await oauth_state_repo.create(state_model)
    await session.commit()

    # 6. Generate authorization URL
    from snackbase.core.config import get_settings
    settings = get_settings()
    
    callback_url = f"{settings.external_url.rstrip('/')}{settings.api_prefix}/auth/oauth/{provider_name}/callback"
    
    auth_url = await handler.get_authorization_url(
        config=config_dict,
        redirect_uri=callback_url,
        state=state_token,
    )

    logger.info(
        "OAuth authorization initiated",
        provider=provider_name,
        account_id=account_id,
        state=state_token,
    )

    return OAuthAuthorizeResponse(
        authorization_url=auth_url,
        state=state_token,
        provider=provider_name,
    )
