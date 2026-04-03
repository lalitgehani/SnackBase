"""SQLAlchemy model for the endpoints table (F8.2).

Custom endpoints allow accounts to define HTTP API handlers stored in the
database. Each endpoint specifies a path, HTTP method, action pipeline, and
response template. Requests arrive via /api/v1/x/{account_slug}/{path} and
are dispatched synchronously with a 30-second timeout.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class EndpointModel(Base):
    """SQLAlchemy model for the endpoints table.

    Attributes:
        id: Primary key (UUID string).
        account_id: Foreign key to accounts table (CASCADE delete).
        name: Human-readable name for this endpoint.
        description: Optional description.
        path: URL path template, e.g. /submit-feedback or /users/:user_id/orders.
            Must start with / and contain only alphanumeric, -, _, /, : characters.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        auth_required: Whether a valid auth token is required (default: True).
        condition: Optional rule expression; request denied (403) if it evaluates False.
        actions: JSON list of action configs to execute sequentially.
        response_template: JSON template for the HTTP response:
            {"status": 200, "body": {...}, "headers": {...}}.
            If None, defaults to 200 with the last action result as body.
        enabled: Whether this endpoint is active.
        created_at: Creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).
        created_by: User ID of the creator (nullable).
    """

    __tablename__ = "endpoints"
    __table_args__ = (
        UniqueConstraint("account_id", "path", "method", name="uq_endpoints_account_path_method"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Endpoint ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name for this endpoint",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description",
    )
    path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL path template starting with /; supports :param segments",
    )
    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="HTTP method: GET, POST, PUT, PATCH, DELETE",
    )
    auth_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether a valid auth token is required",
    )
    condition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional rule expression; request denied (403) if evaluates False",
    )
    actions: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
        comment="Ordered list of action configs to execute",
    )
    response_template: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment='Response template: {"status": 200, "body": {...}, "headers": {...}}',
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Whether this endpoint is active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp (UTC)",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID of the creator",
    )

    def __repr__(self) -> str:
        return (
            f"<Endpoint(id={self.id}, method={self.method!r}, "
            f"path={self.path!r}, enabled={self.enabled})>"
        )
