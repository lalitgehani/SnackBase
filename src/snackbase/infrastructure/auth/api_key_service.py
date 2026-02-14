import hashlib
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from snackbase.infrastructure.persistence.models.api_key import APIKeyModel

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.auth.token_codec import TokenCodec
from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType
from snackbase.infrastructure.persistence.models.token_blacklist import TokenBlacklistModel

logger = get_logger(__name__)


class APIKeyRepositoryProtocol(Protocol):
    """Protocol for APIKeyRepository to avoid circular imports."""

    async def get_by_hash(self, key_hash: str) -> bool: ...


class APIKeyService:
    """Service for managing API keys."""

    @staticmethod
    def hash_key(key: str) -> str:
        """Compute SHA-256 hash of a key.

        Args:
            key: Plaintext API key.

        Returns:
            SHA-256 hex digest.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_api_key(
        self,
        session: AsyncSession,
        user_id: str,
        email: str,
        account_id: str,
        role: str,
        name: str,
        permissions: list[str] = [],
        expires_at: datetime | None = None,
    ) -> tuple[str, "APIKeyModel"]:
        """Create a new JWT-like API key and store it in the database.

        Args:
            session: SQLAlchemy async session.
            user_id: ID of the user owning the key.
            email: Email of the user.
            account_id: ID of the account.
            role: Role of the user.
            name: Human-readable name for the key.
            permissions: List of permissions.
            expires_at: Optional expiration timestamp.

        Returns:
            tuple: (plaintext_key, APIKeyModel)
        """
        token_id = str(uuid.uuid4())
        payload = TokenPayload(
            version=1,
            type=TokenType.API_KEY,
            user_id=user_id,
            email=email,
            account_id=account_id,
            role=role,
            permissions=permissions,
            issued_at=int(datetime.now(timezone.utc).timestamp()),
            expires_at=int(expires_at.timestamp()) if expires_at else None,
            token_id=token_id,
        )

        settings = get_settings()
        plaintext_key = TokenCodec.encode(payload, settings.token_secret)
        key_hash = self.hash_key(plaintext_key)

        # Store in database
        from snackbase.infrastructure.persistence.models.api_key import APIKeyModel

        model = APIKeyModel(
            id=token_id,
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            account_id=account_id,
            expires_at=expires_at,
        )
        session.add(model)
        await session.flush()

        logger.info("API Key created", key_id=token_id, user_id=user_id, name=name)
        return plaintext_key, model

    async def revoke_api_key(
        self,
        token_id: str,
        session: AsyncSession,
        reason: str | None = None,
    ) -> None:
        """Revoke an API key by adding it to the blacklist.

        Args:
            token_id: The token_id to revoke.
            session: SQLAlchemy async session.
            reason: Optional reason for revocation.
        """
        blacklist_entry = TokenBlacklistModel(
            id=token_id,
            token_type=TokenType.API_KEY,
            reason=reason,
        )
        session.add(blacklist_entry)
        logger.info("API Key revoked and added to blacklist", token_id=token_id)

    @staticmethod
    def mask_key(key: str) -> str:
        """Mask an API key for display.

        Format: sb_ak.EY...SIGN

        Args:
            key: The full plaintext key or hash.

        Returns:
            Masked key string.
        """
        # If it's the new format (3 parts separated by dots)
        parts = key.split(".")
        if len(parts) == 3:
            prefix = parts[0]
            payload = parts[1]
            signature = parts[2]
            return f"{prefix}.{payload[:4]}...{signature[-4:]}"

        # Fallback for legacy or hashes
        if len(key) > 12:
            return f"{key[:6]}...{key[-4:]}"
        return "****"


# Global service instance
api_key_service = APIKeyService()
