"""Authentication infrastructure components.

This module provides password hashing, JWT token services, and
other authentication-related utilities.
"""

from snackbase.infrastructure.auth.jwt_service import (
    InvalidTokenError,
    JWTError,
    JWTService,
    TokenExpiredError,
    jwt_service,
)
from snackbase.infrastructure.auth.password_hasher import (
    hash_password,
    needs_rehash,
    verify_password,
)

__all__ = [
    "InvalidTokenError",
    "JWTError",
    "JWTService",
    "TokenExpiredError",
    "hash_password",
    "jwt_service",
    "needs_rehash",
    "verify_password",
]
