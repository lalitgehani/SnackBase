"""SQLAlchemy model for refresh tokens.

Stores refresh tokens for JWT token rotation and invalidation.
Each token is stored with a hash for secure lookup.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class RefreshTokenModel(Base):
    """Refresh token model for JWT token rotation.

    Stores refresh tokens with their hash for secure validation and
    supports token revocation for security.
    """

    __tablename__ = "refresh_tokens"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Token hash (SHA-256) - indexed for fast lookup
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # User and account association
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Token state
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("UserModel", back_populates="refresh_tokens")
    account = relationship("AccountModel", back_populates="refresh_tokens")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_refresh_tokens_user_account", "user_id", "account_id"),
    )

    def __repr__(self) -> str:
        return f"RefreshTokenModel(id={self.id!r}, user_id={self.user_id!r}, is_revoked={self.is_revoked!r})"
