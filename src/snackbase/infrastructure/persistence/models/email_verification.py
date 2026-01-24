"""SQLAlchemy model for email verification tokens.

Stores hashes of verification tokens sent to users to verify their email addresses.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class EmailVerificationTokenModel(Base):
    """SQLAlchemy model for the email_verification_tokens table.

    Attributes:
        id: Primary key (UUID string).
        user_id: Foreign key to users table.
        email: Email address to be verified.
        token_hash: SHA-256 hash of the verification token.
        expires_at: Timestamp when the token expires.
        used_at: Timestamp when the token was used (nullable).
        created_at: Timestamp when the token was created.
    """

    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Token ID (UUID)",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to users table",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email address to be verified",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of the verification token",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp when the token expires",
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the token was used",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the token was created",
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(  # noqa: F821
        "UserModel",
        back_populates="email_verification_tokens",
    )

    __table_args__ = (
        # Unique constraint on (user_id, email) to prevent multiple active tokens for same email
        UniqueConstraint("user_id", "email", name="uq_email_verification_user_email"),
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, email={self.email})>"
