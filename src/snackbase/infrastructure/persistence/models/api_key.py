"""SQLAlchemy model for API keys.

API keys provide programmatic access for superadmin operations.
Only SHA-256 hashes are stored for security.
"""

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class APIKeyModel(Base):
    """SQLAlchemy model for the api_keys table.

    Attributes:
        id: Primary key (UUID string).
        key_hash: SHA-256 hash of the API key.
        name: Human-readable name for the key.
        user_id: Foreign key to users table.
        account_id: Foreign key to accounts table.
        scopes: JSON list of scopes (optional).
        expires_at: Optional expiration timestamp.
        is_active: Whether the key is active (soft delete).
        last_used_at: Timestamp of last successful usage.
        created_at: Timestamp when the key was created.
        updated_at: Timestamp when the key was last updated.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="API key ID (UUID)",
    )
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of the API key",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name for the API key",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to users table",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="JSON list of permission scopes",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Optional expiration timestamp",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether the API key is active (soft delete)",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful usage",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel")  # noqa: F821
    account: Mapped["AccountModel"] = relationship("AccountModel")  # noqa: F821

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id})>"
