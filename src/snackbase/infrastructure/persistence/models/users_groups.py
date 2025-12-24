"""SQLAlchemy model for the users_groups junction table.

Implements the many-to-many relationship between users and groups.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class UsersGroupsModel(Base):
    """Junction table for many-to-many relationship between users and groups.

    Attributes:
        user_id: Foreign key to users table.
        group_id: Foreign key to groups table.
    """

    __tablename__ = "users_groups"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Foreign key to users table",
    )
    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Foreign key to groups table",
    )

    def __repr__(self) -> str:
        return f"<UsersGroups(user_id={self.user_id}, group_id={self.group_id})>"
