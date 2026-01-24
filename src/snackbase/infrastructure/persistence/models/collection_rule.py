"""SQLAlchemy model for the collection_rules table.

Collection rules store row-level security rules for collections.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class CollectionRuleModel(Base):
    """SQLAlchemy model for the collection_rules table.

    Each collection has one rule set defining access control for 5 operations.
    Rules can be NULL (locked), empty string (public), or an expression.

    Attributes:
        id: Primary key (UUID string).
        collection_id: Foreign key to collections table.
        list_rule: Filter expression for listing records.
        view_rule: Filter expression for viewing single record.
        create_rule: Validation expression for creating records.
        update_rule: Filter/validation expression for updates.
        delete_rule: Filter expression for deletions.
        list_fields: Fields visible in list operations.
        view_fields: Fields visible in view operations.
        create_fields: Fields allowed in create requests.
        update_fields: Fields allowed in update requests.
        created_at: Timestamp when the rule was created.
        updated_at: Timestamp when the rule was last updated.
    """

    __tablename__ = "collection_rules"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Collection rule ID (UUID)",
    )
    collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key to collections table",
    )

    # 5 operation rules (NULL = locked, "" = public, "expr" = filter)
    list_rule: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Filter expression for listing records",
    )
    view_rule: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Filter expression for viewing single record",
    )
    create_rule: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Validation expression for creating records",
    )
    update_rule: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Filter/validation expression for updates",
    )
    delete_rule: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Filter expression for deletions",
    )

    # Field-level permissions per operation
    list_fields: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="*",
        comment="Fields visible in list operations (JSON array or '*')",
    )
    view_fields: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="*",
        comment="Fields visible in view operations (JSON array or '*')",
    )
    create_fields: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="*",
        comment="Fields allowed in create requests (JSON array or '*')",
    )
    update_fields: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="*",
        comment="Fields allowed in update requests (JSON array or '*')",
    )

    # Timestamps
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

    def __repr__(self) -> str:
        return f"<CollectionRule(id={self.id}, collection_id={self.collection_id})>"
