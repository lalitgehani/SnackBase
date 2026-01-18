"""OAuth authentication API routes.

Provides endpoints for OAuth 2.0 authorization flows.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services import AccountCodeGenerator
from snackbase.infrastructure.api.schemas.auth_schemas import (
    AccountResponse,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    UserResponse,
)
from snackbase.infrastructure.auth import (
    generate_random_password,
    hash_password,
    jwt_service,
)
from snackbase.infrastructure.configuration.providers.oauth import (
    AppleOAuthHandler,
    GitHubOAuthHandler,
    GoogleOAuthHandler,
    MicrosoftOAuthHandler,
)
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    RefreshTokenModel,
    UserModel,
)
from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    ConfigurationRepository,
    OAuthStateRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
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
            repository=ConfigurationRepository(session),
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

    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    state_model = OAuthStateModel(
        id=str(uuid.uuid4()),
        provider_name=provider_name,
        state_token=state_token,
        redirect_uri=request_body.redirect_uri,
        expires_at=expires_at,
        metadata_={"account_id": account_id, "account_name": request_body.account_name},
    )

    await oauth_state_repo.create(state_model)
    await session.commit()

    # 6. Generate authorization URL
    auth_url = await handler.get_authorization_url(
        config=config_dict,
        redirect_uri=request_body.redirect_uri,
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


@router.post(
    "/{provider_name}/callback",
    status_code=status.HTTP_200_OK,
    response_model=OAuthCallbackResponse,
    responses={
        400: {"description": "Invalid state or OAuth error"},
        401: {"description": "Inactive user"},
        404: {"description": "Provider not configured"},
    },
)
async def callback(
    provider_name: str,
    request_body: OAuthCallbackRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> OAuthCallbackResponse:
    """Complete OAuth authorization flow.

    Validates the state token, exchanges the authorization code for tokens,
    and creates or updates the user record. Returns JWT tokens.

    Flow:
    1. Validate state token and check expiration
    2. Resolve provider configuration
    3. Exchange code for tokens via provider handler
    4. Fetch user info via provider handler
    5. Link to existing user or create new user/account
    6. Generate JWT tokens and return response
    """
    logger.debug("OAuth callback: Step 1 - Starting state validation")

    # 1. State validation and deletion
    oauth_state_repo = OAuthStateRepository(session)
    logger.debug("OAuth callback: Step 1.1 - Created OAuthStateRepository")

    state_model = await oauth_state_repo.get_by_token(request_body.state)
    logger.debug("OAuth callback: Step 1.2 - Retrieved state model", found=state_model is not None)

    if not state_model:
        logger.info("OAuth callback failed: invalid state token", state=request_body.state)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state token",
        )

    logger.debug("OAuth callback: Step 1.3 - Getting expires_at attribute")
    # Check expiration - handle both naive and aware datetimes from DB
    expires_at = state_model.expires_at
    logger.debug("OAuth callback: Step 1.4 - Got expires_at", expires_at=str(expires_at))

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        logger.info("OAuth callback failed: state token expired", state=request_body.state)
        await oauth_state_repo.delete(state_model.id)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State token expired",
        )

    logger.debug("OAuth callback: Step 1.5 - Checking provider name")
    # Provider must match
    if state_model.provider_name != provider_name:
        logger.info(
            "OAuth callback failed: provider mismatch",
            expected=state_model.provider_name,
            actual=provider_name,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch",
        )

    logger.debug("OAuth callback: Step 1.6 - Deleting state (single-use)")
    # Delete state after validation (single-use)
    await oauth_state_repo.delete(state_model.id)
    logger.debug("OAuth callback: Step 1.7 - State deleted")

    # 2. Resolve provider configuration
    logger.debug("OAuth callback: Step 2 - Getting config registry")
    config_registry = getattr(request.app.state, "config_registry", None)
    if not config_registry:
        logger.error("Configuration registry not found in app state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System configuration error",
        )
    logger.debug("OAuth callback: Step 2.1 - Got config registry")

    account_id = (
        state_model.metadata_.get("account_id")
        if state_model.metadata_
        else "00000000-0000-0000-0000-000000000000"
    )

    try:
        config_dict = await config_registry.get_effective_config(
            category="auth_providers",
            provider_name=provider_name,
            account_id=account_id,
            repository=ConfigurationRepository(session),
        )
    except Exception as e:
        logger.error("Error retrieving provider configuration", provider=provider_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving provider configuration",
        )

    if not config_dict:
        logger.info(
            "OAuth callback failed: provider not configured",
            provider=provider_name,
            account_id=account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not configured",
        )

    # 3. Get provider handler
    handler = OAUTH_HANDLERS.get(provider_name)
    if not handler:
        logger.info("OAuth callback failed: no handler for provider", provider=provider_name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' handler not found",
        )

    # 4. Exchange code for tokens
    try:
        tokens = await handler.exchange_code_for_tokens(
            config=config_dict,
            code=request_body.code,
            redirect_uri=request_body.redirect_uri,
        )
    except Exception as e:
        logger.error("OAuth token exchange failed", provider=provider_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth token exchange failed: {str(e)}",
        )

    access_token_provider = tokens.get("access_token")
    if not access_token_provider:
        logger.error("OAuth token exchange failed: access_token not returned", provider=provider_name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token not returned by provider",
        )

    # 5. Fetch user info
    try:
        user_info = await handler.get_user_info(config=config_dict, access_token=access_token_provider)
    except Exception as e:
        logger.error("OAuth user info fetch failed", provider=provider_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth user info fetch failed: {str(e)}",
        )

    external_id = user_info.get("id")
    email = user_info.get("email")
    if not external_id or not email:
        logger.error(
            "OAuth user info missing required fields",
            provider=provider_name,
            has_id=bool(external_id),
            has_email=bool(email),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider did not return required user info (id/email)",
        )

    # 6. User lookup and provisioning
    user_repo = UserRepository(session)
    account_repo = AccountRepository(session)
    role_repo = RoleRepository(session)

    user = await user_repo.get_by_external_id(provider_name, external_id)
    is_new_user = False
    is_new_account = False

    if user:
        # Update existing user
        user.external_email = email
        user.profile_data = user_info
        user.last_login = datetime.now(UTC)
        await user_repo.update(user)
    else:
        # Create new user
        is_new_user = True

        # Check if we need to create a new account (self-provisioning)
        if account_id == "00000000-0000-0000-0000-000000000000":
            # Check for single-tenant mode
            settings = get_settings()

            if settings.single_tenant_mode:
                # Single-tenant mode: join configured account with 'user' role
                logger.debug("OAuth registration in single-tenant mode")
                account_model = await account_repo.get_by_slug(settings.single_tenant_account)
                if not account_model:
                    logger.error(
                        "Single-tenant account not found for OAuth",
                        configured_slug=settings.single_tenant_account,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Configured single-tenant account not found",
                    )
                account_id = account_model.id
                is_new_account = False

                # Get 'user' role for single-tenant mode
                user_role = await role_repo.get_by_name("user")
                if not user_role:
                    logger.error("User role not found in database")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="System configuration error: user role missing",
                    )

                user = UserModel(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    email=email,
                    password_hash=hash_password(generate_random_password()),
                    role_id=user_role.id,
                    is_active=True,
                    auth_provider="oauth",
                    auth_provider_name=provider_name,
                    external_id=external_id,
                    external_email=email,
                    profile_data=user_info,
                )
                await user_repo.create(user)

                logger.info(
                    "OAuth user registered in single-tenant mode",
                    account_id=account_id,
                    user_id=user.id,
                    role="user",
                )
            else:
                # Multi-tenant mode: create new account
                is_new_account = True
                # Create account logic (similar to register route)
                existing_codes = await account_repo.get_all_account_codes()
                new_account_id = str(uuid.uuid4())
                account_code = AccountCodeGenerator.generate(existing_codes)

                from snackbase.domain.services import SlugGenerator

                # Use user-provided account name, fall back to Google profile name
                provided_account_name = (
                    state_model.metadata_.get("account_name")
                    if state_model.metadata_
                    else None
                )
                display_name = provided_account_name or user_info.get("name") or email.split("@")[0]
                slug = SlugGenerator.generate(display_name)

                # Ensure slug uniqueness
                base_slug = slug
                counter = 1
                while await account_repo.slug_exists(slug):
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                account_model = AccountModel(
                    id=new_account_id,
                    account_code=account_code,
                    slug=slug,
                    name=display_name,
                )
                await account_repo.create(account_model)
                account_id = new_account_id

                # Create user record with 'admin' role
                admin_role = await role_repo.get_by_name("admin")
                if not admin_role:
                    logger.error("Admin role not found in database")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="System configuration error: admin role missing",
                    )

                user = UserModel(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    email=email,
                    password_hash=hash_password(generate_random_password()),
                    role_id=admin_role.id,
                    is_active=True,
                    auth_provider="oauth",
                    auth_provider_name=provider_name,
                    external_id=external_id,
                    external_email=email,
                    profile_data=user_info,
                )
                await user_repo.create(user)

                # Add to pii_access group for new account
                from snackbase.domain.services.pii_masking_service import PIIMaskingService
                from snackbase.infrastructure.persistence.models import GroupModel
                from snackbase.infrastructure.persistence.repositories import GroupRepository

                group_repo = GroupRepository(session)
                pii_group = GroupModel(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    name=PIIMaskingService.PII_ACCESS_GROUP,
                    description="Users in this group can view unmasked PII data",
                )
                await group_repo.create(pii_group)
                await group_repo.add_user(group_id=pii_group.id, user_id=user.id)
        else:
            # Join existing account
            account_model = await account_repo.get_by_id(account_id)
            if not account_model:
                logger.error("OAuth callback failed: target account not found", account_id=account_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target account for OAuth flow not found",
                )

            # Create user record with 'admin' role
            admin_role = await role_repo.get_by_name("admin")
            if not admin_role:
                logger.error("Admin role not found in database")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="System configuration error: admin role missing",
                )

            user = UserModel(
                id=str(uuid.uuid4()),
                account_id=account_id,
                email=email,
                password_hash=hash_password(generate_random_password()),
                role_id=admin_role.id,
                is_active=True,
                auth_provider="oauth",
                auth_provider_name=provider_name,
                external_id=external_id,
                external_email=email,
                profile_data=user_info,
            )
            await user_repo.create(user)

    if not user.is_active:
        logger.info("OAuth callback failed: user inactive", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    # 7. Generate JWT tokens
    # Always explicitly load role and account to avoid lazy loading with async driver
    role = await role_repo.get_by_id(user.role_id)
    account = await account_repo.get_by_id(user.account_id)

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role=role.name,
    )
    refresh_token, token_id = jwt_service.create_refresh_token(
        user_id=user.id,
        account_id=user.account_id,
    )
    expires_in = jwt_service.get_expires_in()

    # Store refresh token
    settings = get_settings()
    refresh_token_repo = RefreshTokenRepository(session)
    refresh_token_model = RefreshTokenModel(
        id=token_id,
        token_hash=refresh_token_repo.hash_token(refresh_token),
        user_id=user.id,
        account_id=user.account_id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    await refresh_token_repo.create(refresh_token_model)

    # Commit all changes in a single transaction
    await session.commit()

    logger.info(
        "OAuth authentication successful",
        provider=provider_name,
        user_id=user.id,
        is_new_user=is_new_user,
    )

    return OAuthCallbackResponse(
        token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        account=AccountResponse(
            id=account.id,
            slug=account.slug,
            name=account.name,
            created_at=account.created_at,
        ),
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        is_new_user=is_new_user,
        is_new_account=is_new_account,
    )
