"""SQLAlchemy model for the accounts table.

Accounts represent isolated tenants in the multi-tenant system.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class AccountModel(Base):
    """SQLAlchemy model for the accounts table.

    Attributes:
        id: Primary key in XX#### format (2 uppercase letters + 4 digits).
        slug: URL-friendly identifier, unique across all accounts.
        name: Display name for the account.
        created_at: Timestamp when the account was created.
        updated_at: Timestamp when the account was last updated.
    """

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        comment="Account ID in XX#### format (e.g., AB1234)",
    )
    slug: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly identifier (3-32 chars)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name for the account",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(  # noqa: F821
        "UserModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    groups: Mapped[list["GroupModel"]] = relationship(  # noqa: F821
        "GroupModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list["InvitationModel"]] = relationship(  # noqa: F821
        "InvitationModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(  # noqa: F821
        "RefreshTokenModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Validate account ID format: 2 uppercase letters + 4 digits
        CheckConstraint(
            "id GLOB '[A-Z][A-Z][0-9][0-9][0-9][0-9]'",
            name="ck_accounts_id_format",
        ),
        # Validate slug format: 3-32 chars, alphanumeric + hyphens
        CheckConstraint(
            "length(slug) >= 3 AND length(slug) <= 32",
            name="ck_accounts_slug_length",
        ),
        Index("ix_accounts_id", "id"),
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, slug={self.slug})>"
