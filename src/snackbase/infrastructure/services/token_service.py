"""Token generation service.

Provides cryptographically secure random token generation for invitations
and other security-sensitive operations.
"""

import secrets


class TokenService:
    """Service for generating secure random tokens."""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token.

        Args:
            length: Number of bytes for the token. Default is 32 bytes (64 hex chars).

        Returns:
            URL-safe hexadecimal token string.
        """
        return secrets.token_hex(length)

    @staticmethod
    def generate_urlsafe_token(length: int = 32) -> str:
        """Generate a URL-safe cryptographically secure random token.

        Args:
            length: Number of bytes for the token. Default is 32 bytes.

        Returns:
            URL-safe token string.
        """
        return secrets.token_urlsafe(length)


# Default token service instance
token_service = TokenService()
