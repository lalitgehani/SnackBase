"""FastAPI dependencies for authentication and authorization.

Provides dependencies for extracting and validating JWT tokens from requests.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.services import PermissionCache
from snackbase.infrastructure.auth import (
    InvalidTokenError,
    TokenExpiredError,
    jwt_service,
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
        logger.info("Authentication failed: missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
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
        
        # Load user groups from database
        # 1. Try to load from PermissionCache
        permission_cache = get_permission_cache(request)
        groups = permission_cache.get_user_groups(user_id)

        # 2. If miss, load from DB
        if groups is None:
            groups = []
            if session is not None:
                from snackbase.infrastructure.persistence.repositories import UserRepository
                
                user_repo = UserRepository(session)
                user = await user_repo.get_by_id_with_groups(user_id)
                
                if user and user.groups:
                    groups = [group.name for group in user.groups]
            
            # 3. Cache the result
            permission_cache.set_user_groups(user_id, groups)

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
    except KeyError as e:
        logger.warning("Authentication failed: missing claim in token", missing_claim=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing claim: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
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
