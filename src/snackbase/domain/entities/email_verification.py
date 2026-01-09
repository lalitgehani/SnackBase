"""Email verification entity.

Stores information about email verification tokens sent to users.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import secrets
import hashlib


@dataclass
class EmailVerificationToken:
    """Email verification token entity.

    Attributes:
        id: Unique identifier (UUID string).
        user_id: ID of the user this token is for.
        email: Email address to be verified.
        token_hash: SHA-256 hash of the verification token.
        expires_at: When the token expires.
        created_at: When the token was created.
        used_at: When the token was used (null if not used).
    """

    user_id: str
    email: str
    token_hash: str
    expires_at: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    used_at: datetime | None = None

    @classmethod
    def generate(cls, user_id: str, email: str, expires_in_seconds: int = 3600) -> tuple["EmailVerificationToken", str]:
        """Generate a new verification token and its entity.

        Args:
            user_id: The ID of the user.
            email: The email address to verify.
            expires_in_seconds: Token lifetime in seconds (default 1 hour).

        Returns:
            A tuple of (EmailVerificationToken entity, raw_token_string).
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        expires_at += timedelta(seconds=expires_in_seconds)

        entity = cls(
            user_id=user_id,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return entity, raw_token

    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not used)."""
        now = datetime.now(timezone.utc)
        return self.used_at is None and self.expires_at > now
