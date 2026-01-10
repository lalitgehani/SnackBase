"""SQLAlchemy model for the users table.

Users belong to accounts and are uniquely identified by (account_id, email).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class UserModel(Base):
    """SQLAlchemy model for the users table.

    Users are scoped to accounts. The same email can exist in multiple accounts
    with different passwords and roles.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        email: User's email address (unique within account).
        password_hash: Hashed password.
        role_id: Foreign key to roles table.
        is_active: Whether the user can log in.
        auth_provider: Authentication provider type ('password', 'oauth', 'saml').
        auth_provider_name: Specific provider name (e.g., 'google', 'github').
        external_id: External provider's user ID for identity linking.
        external_email: Email from external provider (may differ from local email).
        profile_data: Additional profile data from external provider (JSON).
        email_verified: Whether the user's email is verified.
        email_verified_at: Timestamp when the email was verified.
        created_at: Timestamp when the user was created.
        updated_at: Timestamp when the user was last updated.
        last_login: Timestamp of last successful login.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="User ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User email address",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password (bcrypt/argon2)",
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
        index=True,
        comment="Foreign key to roles table",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the user can log in",
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="Whether the user's email is verified",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when the email was verified",
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
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last successful login",
    )
    auth_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="password",
        comment="Authentication provider type ('password', 'oauth', 'saml')",
    )
    auth_provider_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific provider name (e.g., 'google', 'github', 'microsoft')",
    )
    external_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="External provider's user ID for identity linking",
    )
    external_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address from external provider (may differ from local email)",
    )
    profile_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional profile data from external provider",
    )

    # Relationships
    account: Mapped["AccountModel"] = relationship(  # noqa: F821
        "AccountModel",
        back_populates="users",
    )
    role: Mapped["RoleModel"] = relationship(  # noqa: F821
        "RoleModel",
        back_populates="users",
    )
    groups: Mapped[list["GroupModel"]] = relationship(  # noqa: F821
        "GroupModel",
        secondary="users_groups",
        back_populates="users",
    )
    invitations_sent: Mapped[list["InvitationModel"]] = relationship(  # noqa: F821
        "InvitationModel",
        back_populates="inviter",
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(  # noqa: F821
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_verification_tokens: Mapped[list["EmailVerificationTokenModel"]] = relationship(  # noqa: F821
        "EmailVerificationTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list["PasswordResetTokenModel"]] = relationship(  # noqa: F821
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def account_code(self) -> str | None:
        """Get the account code from the related account.
        
        Note: This requires the 'account' relationship to be loaded.
        """
        if hasattr(self, "account") and self.account:
            return self.account.account_code
        return None

    @property
    def account_name(self) -> str | None:
        """Get the account name from the related account.
        
        Note: This requires the 'account' relationship to be loaded.
        """
        if hasattr(self, "account") and self.account:
            return self.account.name
        return None

    @property
    def role_name(self) -> str | None:
        """Get the role name from the related role.
        
        Note: This requires the 'role' relationship to be loaded.
        """
        if hasattr(self, "role") and self.role:
            return self.role.name
        return None

    __table_args__ = (
        # Unique constraint on (account_id, email)
        UniqueConstraint("account_id", "email", name="uq_users_account_email"),
        Index("ix_users_account_email", "account_id", "email"),
        # Indexes for authentication provider tracking
        Index("ix_users_auth_provider", "auth_provider"),
        Index("ix_users_auth_provider_name_external_id", "auth_provider_name", "external_id"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, account_id={self.account_id})>"
