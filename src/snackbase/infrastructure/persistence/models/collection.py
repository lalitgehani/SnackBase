"""SQLAlchemy model for the collections table.

Collections store metadata about user-created dynamic data tables.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class CollectionModel(Base):
    """SQLAlchemy model for the collections table.

    Collections store schema definitions for dynamic data tables.
    The actual data is stored in separate tables created when collections are defined.

    Attributes:
        id: Primary key (UUID string).
        name: Collection name (used in API routes).
        schema: JSON schema defining fields, types, and constraints.
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
    migration_revision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Alembic migration revision ID that created/last modified this collection",
    )

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name={self.name})>"
