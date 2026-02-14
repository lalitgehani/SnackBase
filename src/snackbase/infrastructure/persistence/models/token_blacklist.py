
"""SQLAlchemy model for revoked tokens.

This model tracks tokens that have been revoked before their natural expiration.
"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class TokenBlacklistModel(Base):
    """SQLAlchemy model for the token_blacklist table.

    Attributes:
        id: Primary key (token ID string).
        token_type: Type of the token (e.g., 'jwt', 'api_key').
        revoked_at: Timestamp when the token was revoked (Unix timestamp).
        reason: Optional reason for revocation.
    """

    __tablename__ = "token_blacklist"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Token ID (jti or custom ID)",
    )
    token_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        comment="Type of token (jwt, api_key, etc.)",
    )
    revoked_at: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Revocation timestamp (Unix epoch)",
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for revocation",
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, type={self.token_type})>"
