"""SQLAlchemy model for the permissions table.

Permissions define role-based access control rules for collections.
Each permission links a role to a collection with CRUD operation rules.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from snackbase.infrastructure.persistence.database import Base


class PermissionModel(Base):
    """SQLAlchemy model for the permissions table.

    Permissions are linked to roles and define access rules per collection.
    Multiple permissions can exist for the same collection (evaluated with OR logic).

    Attributes:
        id: Auto-incrementing primary key.
        role_id: Foreign key to roles table.
        collection: Collection name this permission applies to (* for all).
        rules: JSON string with CRUD rules structure:
            {
                "create": {"rule": "expression", "fields": ["field1"] or "*"},
                "read": {"rule": "expression", "fields": ["field1"] or "*"},
                "update": {"rule": "expression", "fields": ["field1"] or "*"},
                "delete": {"rule": "expression", "fields": ["field1"] or "*"}
            }
        created_at: Timestamp when the permission was created.
        updated_at: Timestamp when the permission was last updated.
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to roles table",
    )
    collection: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Collection name (* for all collections)",
    )
    rules: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON with CRUD rules: {create, read, update, delete}",
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
    role: Mapped["RoleModel"] = relationship(  # noqa: F821
        "RoleModel",
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, role_id={self.role_id}, collection={self.collection})>"
