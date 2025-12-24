"""JWT token service.

Provides JWT token creation and validation for authentication.
Supports access tokens and refresh tokens with configurable expiration.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from snackbase.core.config import get_settings


class JWTError(Exception):
    """Base exception for JWT-related errors."""

    pass


class TokenExpiredError(JWTError):
    """Raised when a token has expired."""

    pass


class InvalidTokenError(JWTError):
    """Raised when a token is invalid."""

    pass


class JWTService:
    """Service for creating and validating JWT tokens.

    Supports both access tokens (short-lived) and refresh tokens (long-lived).
    """

    ALGORITHM = "HS256"
    ISSUER = "snackbase"

    def __init__(self, secret_key: str | None = None) -> None:
        """Initialize the JWT service.

        Args:
            secret_key: Secret key for signing tokens. If not provided,
                        uses the configured secret key from settings.
        """
        self._secret_key = secret_key

    @property
    def secret_key(self) -> str:
        """Get the secret key for signing tokens."""
        if self._secret_key:
            return self._secret_key
        return get_settings().secret_key

    def create_access_token(
        self,
        user_id: str,
        account_id: str,
        email: str,
        role: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create an access token.

        Args:
            user_id: The user's unique identifier.
            account_id: The account ID the user belongs to.
            email: The user's email address.
            role: The user's role name.
            expires_delta: Custom expiration time. Defaults to config value.

        Returns:
            Encoded JWT access token.
        """
        settings = get_settings()
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "iss": self.ISSUER,
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "user_id": user_id,
            "account_id": account_id,
            "email": email,
            "role": role,
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)

    def create_refresh_token(
        self,
        user_id: str,
        account_id: str,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str]:
        """Create a refresh token.

        Args:
            user_id: The user's unique identifier.
            account_id: The account ID the user belongs to.
            expires_delta: Custom expiration time. Defaults to config value.

        Returns:
            Tuple of (encoded JWT refresh token, token ID for storage).
        """
        settings = get_settings()
        if expires_delta is None:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        token_id = str(uuid.uuid4())

        payload = {
            "iss": self.ISSUER,
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "jti": token_id,
            "user_id": user_id,
            "account_id": account_id,
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM), token_id

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: The encoded JWT token.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.ALGORITHM],
                issuer=self.ISSUER,
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError("Invalid token") from e

    def validate_refresh_token(self, token: str) -> dict[str, Any]:
        """Validate that a token is a refresh token and decode it.

        Args:
            token: The encoded JWT token.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or not a refresh token.
        """
        payload = self.decode_token(token)
        if payload.get("type") != "refresh":
            raise InvalidTokenError("Not a refresh token")
        return payload

    def validate_access_token(self, token: str) -> dict[str, Any]:
        """Validate that a token is an access token and decode it.

        Args:
            token: The encoded JWT token.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or not an access token.
        """
        payload = self.decode_token(token)
        if payload.get("type") != "access":
            raise InvalidTokenError("Not an access token")
        return payload

    def get_expires_in(self, expires_delta: timedelta | None = None) -> int:
        """Get the expiration time in seconds.

        Args:
            expires_delta: Custom expiration time. Defaults to config value.

        Returns:
            Expiration time in seconds.
        """
        if expires_delta is None:
            settings = get_settings()
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        return int(expires_delta.total_seconds())


# Default JWT service instance
jwt_service = JWTService()
