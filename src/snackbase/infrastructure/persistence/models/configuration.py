"""SQLAlchemy model for the configurations table.

Configurations represent external service provider settings (auth, email, storage, etc.)
with support for hierarchical configuration (system-level defaults + account-level overrides).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base
from datetime import datetime, timezone


class ConfigurationModel(Base):
    """SQLAlchemy model for the configurations table.

    Attributes:
        id: Primary key (UUID).
        account_id: Foreign key to accounts table (always populated, never NULL).
        category: Configuration category (e.g., 'auth_providers', 'email_providers').
        provider_name: Provider identifier (e.g., 'google', 'ses', 's3').
        display_name: Human-readable provider name.
        logo_url: Optional path to provider logo.
        config_schema: Optional JSON Schema for configuration validation.
        config: Provider configuration as encrypted JSON.
        enabled: Whether this configuration is active.
        is_builtin: Whether this is a built-in provider (cannot be deleted).
        is_system: Whether this is a system-level config (true for SY0000).
        priority: Display order priority (lower = higher priority).
        created_at: Timestamp when the configuration was created.
        updated_at: Timestamp when the configuration was last updated.
    """

    __tablename__ = "configurations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Configuration ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to accounts table (always populated)",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Configuration category (e.g., 'auth_providers', 'email_providers')",
    )
    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Provider identifier (e.g., 'google', 'ses', 's3')",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable provider name",
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to provider logo",
    )
    config_schema: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="JSON Schema for configuration validation",
    )
    config: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        comment="Provider configuration as encrypted JSON",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="1",
        comment="Whether this configuration is active",
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="Built-in providers cannot be deleted",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="True for system-level configs (SY0000), false for account-level",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Display order priority (lower = higher priority)",
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
    account: Mapped["AccountModel"] = relationship(  # noqa: F821
        "AccountModel",
        back_populates="configurations",
    )

    __table_args__ = (
        # Unique constraint: same provider can exist at system and account levels
        UniqueConstraint(
            "category",
            "provider_name",
            "account_id",
            name="uq_configurations_category_provider_account",
        ),
        # Index for efficient lookups by category and account
        Index("ix_configurations_category_account", "category", "account_id"),
        # Index for efficient lookups by category and provider
        Index("ix_configurations_category_provider", "category", "provider_name"),
        # Index for efficient lookups by is_system flag
        Index("ix_configurations_is_system", "is_system"),
    )

    def __repr__(self) -> str:
        return (
            f"<Configuration(id={self.id}, category={self.category}, "
            f"provider={self.provider_name}, account_id={self.account_id})>"
        )


class OAuthStateModel(Base):
    """SQLAlchemy model for the oauth_states table.

    Used to store temporary OAuth state tokens for flow validation and CSRF protection.

    Attributes:
        id: Primary key (UUID).
        provider_name: Target OAuth provider name.
        state_token: Secure random state token.
        redirect_uri: Redirect URI to return to after flow completion.
        code_verifier: Optional PKCE code verifier.
        metadata: Optional additional metadata for the flow.
        expires_at: Token expiration timestamp.
        created_at: Token creation timestamp.
    """

    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="OAuth state ID (UUID)",
    )
    provider_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target OAuth provider name",
    )
    state_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Secure random state token",
    )
    redirect_uri: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Redirect URI to return to after flow completion",
    )
    code_verifier: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional PKCE code verifier",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Optional additional metadata for the flow",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Token expiration timestamp",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Token creation timestamp",
    )

    __table_args__ = (
        Index("ix_oauth_states_state_token", "state_token"),
        Index("ix_oauth_states_expires_at", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if the state token has expired."""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<OAuthState(id={self.id}, provider={self.provider_name}, "
            f"token={self.state_token[:8]}...)>"
        )
