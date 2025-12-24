"""SQLAlchemy model for the groups table.

Groups allow organizing users within an account for permission management.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class GroupModel(Base):
    """SQLAlchemy model for the groups table.

    Groups are account-scoped and can be used in permission rules
    to grant access based on group membership.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table.
        name: Group name (unique within account).
        description: Optional description.
        created_at: Timestamp when the group was created.
        updated_at: Timestamp when the group was last updated.
    """

    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Group ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Group name",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Description of the group's purpose",
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
        back_populates="groups",
    )
    users: Mapped[list["UserModel"]] = relationship(  # noqa: F821
        "UserModel",
        secondary="users_groups",
        back_populates="groups",
    )

    __table_args__ = (
        # Unique constraint on (account_id, name)
        UniqueConstraint("account_id", "name", name="uq_groups_account_name"),
        Index("ix_groups_account_name", "account_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name}, account_id={self.account_id})>"
