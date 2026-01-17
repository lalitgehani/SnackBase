"""Service for API key generation and validation."""

import hashlib
import secrets
import string
from typing import Protocol

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class APIKeyRepositoryProtocol(Protocol):
    """Protocol for APIKeyRepository to avoid circular imports."""
    async def get_by_hash(self, key_hash: str) -> bool: ...


class APIKeyService:
    """Service for managing API keys."""

    PREFIX = "sb_sk"
    RANDOM_PART_LENGTH = 32

    @staticmethod
    def generate_random_string(length: int = RANDOM_PART_LENGTH) -> str:
        """Generate a cryptographically secure random string.

        Args:
            length: Length of the random part.

        Returns:
            Secure random string.
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_key_value(self, account_code: str) -> str:
        """Generate a new API key value.

        Format: sb_sk_<account_code>_<random_32_chars>

        Args:
            account_code: The account code to include in the key.

        Returns:
            The full plaintext API key.
        """
        random_part = self.generate_random_string()
        return f"{self.PREFIX}_{account_code}_{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Compute SHA-256 hash of a key.

        Args:
            key: Plaintext API key.

        Returns:
            SHA-256 hex digest.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def mask_key(key_or_hash: str, is_hash: bool = False) -> str:
        """Mask an API key for display.

        Format: sb_sk_SY...o5p6

        Args:
            key_or_hash: Either the full key or its hash.
            is_hash: Whether the input is a hash (in which case we can't show prefix).

        Returns:
            Masked key string.
        """
        if is_hash:
            # If it's a hash, we can't reconstruct the original prefix precisely 
            # without database context, so we just show start/end of hash
            return f"{key_or_hash[:6]}...{key_or_hash[-4:]}"
        
        parts = key_or_hash.split("_")
        if len(parts) < 3:
            return "sb_sk_invalid"
            
        prefix = parts[0]
        type_code = parts[1]
        account_code = parts[2]
        
        # If the key has the expected format: sb_sk_ACCOUNT_SECRET
        # parts will be ["sb", "sk", "ACCOUNT", "SECRET"]
        if len(parts) == 4:
            account = parts[2]
            secret = parts[3]
            return f"sb_sk_{account}_{secret[:4]}...{secret[-4:]}"
            
        return f"{key_or_hash[:10]}...{key_or_hash[-4:]}"

    async def generate_unique_key(self, account_code: str, repository: APIKeyRepositoryProtocol) -> str:
        """Generate a unique API key, checking for collisions.

        Args:
            account_code: The account code to include in the key.
            repository: APIKeyRepository instance.

        Returns:
            A unique plaintext API key.
        """
        # Max 10 attempts to prevent infinite loop (highly unlikely with 256-bit entropy)
        for _ in range(10):
            key = self.generate_key_value(account_code)
            key_hash = self.hash_key(key)
            if not await repository.get_by_hash(key_hash):
                return key
        
        logger.error("Failed to generate a unique API key after 10 attempts")
        raise RuntimeError("Collision detected multiple times during API key generation")


# Global service instance
api_key_service = APIKeyService()
