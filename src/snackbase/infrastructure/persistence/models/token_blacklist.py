"""SQLAlchemy model for token blacklist.

Used for revoking JWTs, API keys, and other SnackBase tokens.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class TokenBlacklistModel(Base):
    """SQLAlchemy model for the token_blacklist table.

    Attributes:
        id: Primary key (token_id from the token payload).
        token_type: Type of the revoked token (e.g., api_key, jwt).
        revoked_at: Unix timestamp when the token was revoked.
        reason: Optional reason for revocation.
    """

    __tablename__ = "token_blacklist"

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Token ID (from payload)",
    )
    token_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of token blacklisted",
    )
    revoked_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=lambda: int(datetime.now(timezone.utc).timestamp()),
        comment="Unix timestamp of revocation",
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reason for revocation",
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, type={self.token_type})>"
