"""SQLAlchemy model for the users table.

Users belong to accounts and are uniquely identified by (account_id, email).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
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
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, account_id={self.account_id})>"
