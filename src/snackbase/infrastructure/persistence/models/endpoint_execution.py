"""SQLAlchemy model for the endpoint_executions table (F8.2).

Each row records the outcome of a single custom endpoint invocation,
including the request snapshot and response body for debugging.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class EndpointExecutionModel(Base):
    """Execution log for a single custom endpoint invocation.

    Attributes:
        id: Primary key (UUID string).
        endpoint_id: Foreign key to endpoints table (CASCADE delete).
        status: Outcome: "success", "failed", or "partial".
        http_status: HTTP status code returned to the caller.
        duration_ms: Wall-clock execution time in milliseconds.
        request_data: Snapshot of the incoming request (body, query, params).
        response_body: The actual response body sent to the caller.
        error_message: Error details when status is "failed" or "partial".
        executed_at: When this execution occurred (UTC).
    """

    __tablename__ = "endpoint_executions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Execution ID (UUID)",
    )
    endpoint_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to endpoints table",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Execution outcome: success, failed, or partial",
    )
    http_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200,
        server_default="200",
        comment="HTTP status code returned to the caller",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Wall-clock execution time in milliseconds",
    )
    request_data: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Snapshot of the incoming request (body, query params, path params)",
    )
    response_body: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Actual response body sent to the caller",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if execution failed",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this execution occurred (UTC)",
    )

    def __repr__(self) -> str:
        return (
            f"<EndpointExecution(id={self.id}, endpoint_id={self.endpoint_id}, "
            f"status={self.status!r}, http_status={self.http_status})>"
        )
