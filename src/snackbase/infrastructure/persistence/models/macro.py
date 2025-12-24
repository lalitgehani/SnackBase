"""SQLAlchemy model for the macros table.

Macros allow defining reusable SQL snippets for permission rules.
They are global (shared across accounts) and managed by superadmins.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class MacroModel(Base):
    """SQLAlchemy model for the macros table.

    Macros store SQL queries that can be referenced in permission rules.

    Attributes:
        id: Auto-incrementing primary key.
        name: Unique name of the macro (referenced as @macro_name).
        description: Optional description of what the macro does.
        sql_query: The SQL SELECT statement.
        parameters: JSON array of parameter names used in the query.
        created_at: Timestamp when the macro was created.
        updated_at: Timestamp when the macro was last updated.
        created_by: User ID of the creator (audit trail).
    """

    __tablename__ = "macros"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique macro name (used as @name in rules)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the macro's purpose",
    )
    sql_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The SQL SELECT query",
    )
    parameters: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="JSON array of parameter names",
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
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID of the creator",
    )

    def __repr__(self) -> str:
        return f"<Macro(id={self.id}, name='{self.name}')>"
