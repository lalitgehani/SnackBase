"""FastAPI dependencies for authentication and authorization.

Provides dependencies for extracting and validating JWT tokens from requests.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth.token_types import (
    AuthenticatedUser as AuthUser,
)
from snackbase.infrastructure.persistence.database import get_db_session

if TYPE_CHECKING:
    from snackbase.domain.services.email_verification_service import EmailVerificationService
    from snackbase.domain.services.password_reset_service import PasswordResetService
    from snackbase.infrastructure.services.email_service import EmailService

logger = get_logger(__name__)


async def get_current_user(
    request: Request,
) -> AuthUser:
    """Extract and validate the current user from the request state.

    The user is populated by the AuthenticationMiddleware.

    Args:
        request: The incoming request.

    Returns:
        AuthUser: The authenticated user's context.

    Raises:
        HTTPException: 401 if authentication failed or is missing.
    """
    if not hasattr(request.state, "authenticated_user"):
        auth_error = getattr(request.state, "auth_error", "Missing authentication credentials")
        logger.info(f"Authentication failed: {auth_error}")
        
        # Specific status code for restricted API keys
        status_code = status.HTTP_401_UNAUTHORIZED
        if "restricted to superadmin" in auth_error:
            status_code = status.HTTP_403_FORBIDDEN
            
        raise HTTPException(
            status_code=status_code,
            detail=auth_error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return request.state.authenticated_user


# Type alias for dependency injection
AuthenticatedUser = Annotated[AuthUser, Depends(get_current_user)]
CurrentUser = AuthUser  # Alias for backward compatibility as a type


# System account ID for superadmins
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"  # Nil UUID
SYSTEM_ACCOUNT_CODE = "SY0000"  # Human-readable code


async def require_superadmin(
    current_user: AuthenticatedUser,
) -> AuthUser:
    """Ensure the current user is a superadmin.

    Superadmins are users linked to the special system account (UUID: nil UUID, Code: SY0000).

    Args:
        current_user: The authenticated user.

    Returns:
        AuthUser: The validated superadmin user.

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

    return int(user.role_id)


@dataclass
class AuthorizationContext:
    """Context for authorization checks.

    Contains user information and role for
    performing authorization checks.
    """

    user: AuthUser
    role_id: int


async def get_authorization_context(
    current_user: AuthenticatedUser,
    role_id: Annotated[int, Depends(get_user_role_id)],
) -> AuthorizationContext:
    """Get authorization context for the current request.

    Args:
        current_user: The authenticated user.
        role_id: User's role_id from database.

    Returns:
        AuthorizationContext with user and role_id.
    """
    return AuthorizationContext(
        user=current_user,
        role_id=role_id,
    )


# Type alias for superadmin dependency injection
SuperadminUser = Annotated[AuthUser, Depends(require_superadmin)]

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
