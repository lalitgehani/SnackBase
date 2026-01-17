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
from snackbase.infrastructure.auth.api_key_service import (
    APIKeyService,
    api_key_service,
)
from snackbase.infrastructure.auth.password_hasher import (
    DUMMY_PASSWORD_HASH,
    generate_random_password,
    hash_password,
    needs_rehash,
    verify_password,
)

__all__ = [
    "DUMMY_PASSWORD_HASH",
    "InvalidTokenError",
    "JWTError",
    "JWTService",
    "TokenExpiredError",
    "generate_random_password",
    "hash_password",
    "jwt_service",
    "api_key_service",
    "APIKeyService",
    "needs_rehash",
    "verify_password",
]

