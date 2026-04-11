"""SQLAlchemy model for the collections table.

Collections store metadata about user-created dynamic data tables and views.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class CollectionModel(Base):
    """SQLAlchemy model for the collections table.

    Collections store schema definitions for dynamic data tables or SQL views.
    The actual data is stored in separate tables created when collections are defined,
    or in SQL views for view collections.

    Attributes:
        id: Primary key (UUID string).
        name: Collection name (used in API routes).
        schema: JSON schema defining fields, types, and constraints.
        type: Collection type - "base" for physical tables, "view" for SQL views.
        view_query: SQL query defining the view (NULL for base collections).
        created_at: Timestamp when the collection was created.
        updated_at: Timestamp when the collection was last updated.
    """

    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Collection ID (UUID)",
    )
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Collection name (3-64 chars, alphanumeric + underscores)",
    )
    schema: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON schema defining fields, types, and constraints",
    )
    type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="base",
        comment="Collection type: 'base' for physical tables, 'view' for SQL views",
    )
    view_query: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="SQL query defining the view (NULL for base collections)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    migration_revision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Alembic migration revision ID that created/last modified this collection",
    )

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name={self.name}, type={self.type})>"
