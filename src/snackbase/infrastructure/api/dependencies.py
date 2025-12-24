"""FastAPI dependencies for authentication and authorization.

Provides dependencies for extracting and validating JWT tokens from requests.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth import (
    InvalidTokenError,
    TokenExpiredError,
    jwt_service,
)

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


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Extract and validate the current user from the Authorization header.

    Args:
        authorization: The Authorization header value (e.g., "Bearer <token>").

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
        raise credentials_exception

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.info("Authentication failed: invalid Authorization header format")
        raise credentials_exception

    token = parts[1]

    try:
        # Validate access token (not refresh token)
        payload = jwt_service.validate_access_token(token)

        return CurrentUser(
            user_id=payload["user_id"],
            account_id=payload["account_id"],
            email=payload["email"],
            role=payload["role"],
        )
    except TokenExpiredError:
        logger.info("Authentication failed: token expired")
        raise credentials_exception
    except InvalidTokenError as e:
        logger.info("Authentication failed: invalid token", error=str(e))
        raise credentials_exception
    except KeyError as e:
        logger.warning("Authentication failed: missing claim in token", missing_claim=str(e))
        raise credentials_exception


# Type alias for dependency injection
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


# System account ID for superadmins
SYSTEM_ACCOUNT_ID = "SY0000"


async def require_superadmin(
    current_user: AuthenticatedUser,
) -> CurrentUser:
    """Ensure the current user is a superadmin.

    Superadmins are users linked to the special system account (SY0000).

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


# Type alias for superadmin dependency injection
SuperadminUser = Annotated[CurrentUser, Depends(require_superadmin)]

