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
from snackbase.infrastructure.auth.token_types import (
    AuthenticatedUser,
    TokenPayload,
    TokenType,
)
from snackbase.infrastructure.auth.token_codec import (
    AuthenticationError,
    TokenCodec,
)
from snackbase.infrastructure.auth.authenticator import Authenticator


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
    "TokenPayload",
    "TokenType",
    "AuthenticationError",
    "TokenCodec",
    "Authenticator",
    "AuthenticatedUser",
]

