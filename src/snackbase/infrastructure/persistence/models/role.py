"""SQLAlchemy model for the roles table.

Roles are global (not account-scoped) and define base permissions for users.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class RoleModel(Base):
    """SQLAlchemy model for the roles table.

    Roles define permission levels for users. Default roles are 'admin' and 'user'.

    Attributes:
        id: Auto-incrementing primary key.
        name: Unique role name.
        description: Optional description of the role's purpose.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Role name (e.g., 'admin', 'user')",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Description of the role's purpose",
    )

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(  # noqa: F821
        "UserModel",
        back_populates="role",
    )
    permissions: Mapped[list["PermissionModel"]] = relationship(  # noqa: F821
        "PermissionModel",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
