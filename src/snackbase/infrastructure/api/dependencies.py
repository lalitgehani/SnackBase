"""FastAPI dependencies for authentication and authorization.

Provides dependencies for extracting and validating JWT tokens from requests.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import PermissionCache
from snackbase.infrastructure.auth import (
    InvalidTokenError,
    TokenExpiredError,
    jwt_service,
    api_key_service,
)
from snackbase.infrastructure.persistence.database import get_db_session

logger = get_logger(__name__)


@dataclass
class CurrentUser:
    """Represents the current authenticated user context.

    Extracted from a valid JWT access token.
    """

    user_id: str
    account_id: str
    email: str
    role: str
    groups: list[str]  # List of group names the user belongs to


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> CurrentUser:
    """Extract and validate the current user from the Authorization header.

    Args:
        authorization: The Authorization header value (e.g., "Bearer <token>").
        session: Database session for loading user groups.

    Returns:
        CurrentUser: The authenticated user's context.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if authorization is None:
        if x_api_key:
            return await get_current_user_from_api_key(x_api_key, request, session)
            
        logger.info("Authentication failed: missing Authorization and X-API-Key headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.info("Authentication failed: invalid Authorization header format")
        raise credentials_exception

    token = parts[1]

    try:
        # Validate access token (not refresh token)
        payload = jwt_service.validate_access_token(token)

        user_id = payload["user_id"]
        
        # Load user info from database or cache
        permission_cache = get_permission_cache(request)
        user_info = permission_cache.get_user_info(user_id)
        
        db_account_id = None
        groups = []

        if user_info:
            groups = user_info["groups"]
            db_account_id = user_info["account_id"]
        elif session is not None:
            from snackbase.infrastructure.persistence.repositories import UserRepository

            user_repo = UserRepository(session)
            user = await user_repo.get_by_id_with_groups(user_id)

            if user:
                db_account_id = user.account_id
                if user.groups:
                    groups = [group.name for group in user.groups]

                # Cache for next time
                permission_cache.set_user_info(user_id, groups, db_account_id)
            else:
                logger.info("Authentication failed: user not found in database", user_id=user_id)
                raise credentials_exception
        else:
            # Without session and cache miss, we can't verify existence.
            # We should fail to be safe.
            logger.warning(
                "Authentication failed: cannot verify user existence (no session/cache hit)",
                user_id=user_id,
            )
            raise credentials_exception

        # Verify that the user actually belongs to the account specified in the token
        if db_account_id and db_account_id != payload["account_id"]:
            logger.warning(
                "Authentication failed: user-account mismatch",
                user_id=user_id,
                token_account_id=payload["account_id"],
                db_account_id=db_account_id,
            )
            # Use InvalidTokenError to trigger 401
            raise InvalidTokenError("User does not belong to this account")

        return CurrentUser(
            user_id=user_id,
            account_id=payload["account_id"],
            email=payload["email"],
            role=payload["role"],
            groups=groups,
        )
    except TokenExpiredError:
        logger.info("Authentication failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        logger.info("Authentication failed: invalid token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        # Re-raise HTTP exceptions from API key validation
        raise
    except KeyError as e:
        logger.warning("Authentication failed: missing claim in token", missing_claim=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing claim: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_api_key(
    api_key: str,
    request: Request,
    session: AsyncSession,
) -> CurrentUser:
    """Validate and extract the current user from an API key.

    Args:
        api_key: The plaintext API key from the X-API-Key header.
        request: FastAPI request object.
        session: Database session.

    Returns:
        CurrentUser: The authenticated user's context.

    Raises:
        HTTPException: 401 if key is invalid/expired, 403 if not superadmin.
    """
    from snackbase.infrastructure.persistence.repositories import (
        APIKeyRepository,
        UserRepository,
    )

    key_hash = api_key_service.hash_key(api_key)
    api_key_repo = APIKeyRepository(session)
    
    key_model = await api_key_repo.get_by_hash(key_hash)
    
    if not key_model:
        logger.info("API Key authentication failed: key not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
        
    # Check expiration
    if key_model.expires_at and key_model.expires_at < datetime.now(key_model.expires_at.tzinfo):
        logger.info("API Key authentication failed: key expired", key_id=key_model.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )
        
    # Load user with groups and role
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from snackbase.infrastructure.persistence.models import UserModel
    
    result = await session.execute(
        select(UserModel)
        .where(UserModel.id == key_model.user_id)
        .options(selectinload(UserModel.groups), selectinload(UserModel.role))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning("API Key authentication failed: user not found", user_id=key_model.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with API key not found",
        )
        
    # Verify user is superadmin (system account)
    if user.account_id != SYSTEM_ACCOUNT_ID:
        logger.warning(
            "API Key access denied: user is not a superadmin",
            user_id=user.id,
            account_id=user.account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API keys are restricted to superadmin users",
        )
        
    # Update last_used_at
    await api_key_repo.update_last_used(key_model.id)
    
    # Audit log the usage (simplified here, will be integrated properly)
    logger.info(
        "API Key used",
        key_id=key_model.id,
        user_id=user.id,
        path=str(request.url.path),
    )
    
    groups = [group.name for group in user.groups] if user.groups else []
    
    return CurrentUser(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role=user.role.name if user.role else "admin",
        groups=groups,
    )


# Type alias for dependency injection
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


# System account ID for superadmins
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"  # Nil UUID
SYSTEM_ACCOUNT_CODE = "SY0000"  # Human-readable code


async def require_superadmin(
    current_user: AuthenticatedUser,
) -> CurrentUser:
    """Ensure the current user is a superadmin.

    Superadmins are users linked to the special system account (UUID: nil UUID, Code: SY0000).

    Args:
        current_user: The authenticated user from the JWT token.

    Returns:
        CurrentUser: The validated superadmin user.

    Raises:
        HTTPException: 403 if user is not a superadmin.
    """
    if current_user.account_id != SYSTEM_ACCOUNT_ID:
        logger.info(
            "Superadmin access denied",
            user_id=current_user.user_id,
            account_id=current_user.account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


def get_permission_cache(request: Request) -> PermissionCache:
    """Get the permission cache from app state.
    
    Args:
        request: FastAPI request object.
        
    Returns:
        PermissionCache instance.
    """
    # Check if permission_cache exists, create if not (for test compatibility)
    if not hasattr(request.app.state, "permission_cache"):
        from snackbase.core.config import get_settings
        settings = get_settings()
        request.app.state.permission_cache = PermissionCache(
            ttl_seconds=settings.permission_cache_ttl_seconds
        )
    
    return request.app.state.permission_cache


async def get_user_role_id(
    current_user: AuthenticatedUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> int:
    """Get the role_id for the current user.
    
    Args:
        current_user: The authenticated user.
        session: Database session.
        
    Returns:
        User's role_id.
        
    Raises:
        HTTPException: 404 if user not found.
    """
    from snackbase.infrastructure.persistence.repositories import UserRepository
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(current_user.user_id)
    
    if user is None:
        logger.warning(
            "User not found in database",
            user_id=current_user.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user.role_id


@dataclass
class AuthorizationContext:
    """Context for authorization checks.
    
    Contains user information, role, and permission cache for
    performing authorization checks.
    """
    
    user: CurrentUser
    role_id: int
    permission_cache: PermissionCache


async def get_authorization_context(
    current_user: AuthenticatedUser,
    role_id: Annotated[int, Depends(get_user_role_id)],
    request: Request,
) -> AuthorizationContext:
    """Get authorization context for the current request.
    
    Args:
        current_user: The authenticated user.
        role_id: User's role_id from database.
        request: FastAPI request object.
        
    Returns:
        AuthorizationContext with user, role_id, and permission cache.
    """
    return AuthorizationContext(
        user=current_user,
        role_id=role_id,
        permission_cache=get_permission_cache(request),
    )


# Type alias for superadmin dependency injection
SuperadminUser = Annotated[CurrentUser, Depends(require_superadmin)]

# Type alias for authorization context dependency injection
AuthContext = Annotated[AuthorizationContext, Depends(get_authorization_context)]


async def get_email_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> "EmailService":
    """Get EmailService instance.

    Args:
        request: FastAPI request object.
        session: Database session.

    Returns:
        EmailService instance.
    """
    from snackbase.infrastructure.persistence.repositories import (
        ConfigurationRepository,
        EmailLogRepository,
        EmailTemplateRepository,
    )
    from snackbase.infrastructure.security.encryption import EncryptionService
    from snackbase.infrastructure.services.email_service import EmailService

    template_repo = EmailTemplateRepository()
    log_repo = EmailLogRepository()
    config_repo = ConfigurationRepository(session)
    
    # Get encryption service from app state
    # Fallback to creating a temporary one if registry is missing (e.g. in tests)
    registry = getattr(request.app.state, "config_registry", None)
    if registry:
        encryption_service = registry.encryption_service
    else:
        from snackbase.core.config import get_settings
        settings = get_settings()
        encryption_service = EncryptionService(settings.secret_key)

    return EmailService(
        template_repository=template_repo,
        log_repository=log_repo,
        config_repository=config_repo,
        encryption_service=encryption_service,
    )


async def get_verification_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    email_service: Annotated["EmailService", Depends(get_email_service)],
) -> "EmailVerificationService":
    """Get EmailVerificationService instance.

    Args:
        session: Database session.
        email_service: Email service dependency.

    Returns:
        EmailVerificationService instance.
    """
    from snackbase.domain.services.email_verification_service import EmailVerificationService
    from snackbase.infrastructure.persistence.repositories import (
        EmailVerificationRepository,
        UserRepository,
    )

    user_repo = UserRepository(session)
    verification_repo = EmailVerificationRepository(session)

    return EmailVerificationService(
        session=session,
        user_repo=user_repo,
        verification_repo=verification_repo,
        email_service=email_service,
    )


async def get_password_reset_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    email_service: Annotated["EmailService", Depends(get_email_service)],
) -> "PasswordResetService":
    """Get PasswordResetService instance.

    Args:
        session: Database session.
        email_service: Email service dependency.

    Returns:
        PasswordResetService instance.
    """
    from snackbase.domain.services.password_reset_service import PasswordResetService
    from snackbase.infrastructure.persistence.repositories import (
        PasswordResetRepository,
        RefreshTokenRepository,
        UserRepository,
    )

    user_repo = UserRepository(session)
    reset_repo = PasswordResetRepository(session)
    refresh_token_repo = RefreshTokenRepository(session)

    return PasswordResetService(
        session=session,
        user_repo=user_repo,
        reset_repo=reset_repo,
        refresh_token_repo=refresh_token_repo,
        email_service=email_service,
    )

