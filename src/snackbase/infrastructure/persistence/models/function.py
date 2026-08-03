"""SQLAlchemy models for Functions (tenant-deployed Python FaaS)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class FunctionModel(Base):
    """Account-scoped function definition (metadata + active version pointer)."""

    __tablename__ = "functions"
    __table_args__ = (
        UniqueConstraint("account_id", "slug", name="uq_functions_account_slug"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Function ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="URL slug unique per account",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description",
    )
    entrypoint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="handler.py",
        server_default="handler.py",
        comment="Entrypoint source file relative path",
    )
    auth_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether a valid auth token is required to invoke",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Whether the function accepts invokes",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
        comment="Lifecycle status: ACTIVE, REMOVED, THROTTLED",
    )
    active_version_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="Currently active function_versions.id",
    )
    grants: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Admin-client capability grants (deny-by-default)",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID of the creator",
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

    def __repr__(self) -> str:
        return (
            f"<Function(id={self.id}, slug={self.slug!r}, "
            f"status={self.status}, enabled={self.enabled})>"
        )


class FunctionVersionModel(Base):
    """Immutable deployed version of a function (source + deps + env path)."""

    __tablename__ = "function_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Version ID (UUID)",
    )
    function_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("functions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to functions table",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Monotonic version number per function",
    )
    source_files: Mapped[dict[str, str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Map of relative path -> source content",
    )
    dependencies: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
        comment="Exact pin list (pkg==ver)",
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Content hash of source_files + dependencies",
    )
    env_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Filesystem path to the version venv",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="User ID who deployed this version",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Deploy timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<FunctionVersion(id={self.id}, function_id={self.function_id}, v={self.version})>"


class FunctionExecutionModel(Base):
    """Per-invocation execution log for a function."""

    __tablename__ = "function_executions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Execution ID (UUID)",
    )
    function_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("functions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to functions table",
    )
    version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("function_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Version that was executed",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="success | failed | timeout",
    )
    http_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200,
        server_default="200",
        comment="HTTP status returned to the caller",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Wall-clock duration in milliseconds",
    )
    request_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Redacted request snapshot",
    )
    response_body: Mapped[Any | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="Response body (truncated/redacted)",
    )
    stdout: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Captured stdout (truncated)",
    )
    stderr: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Captured stderr (truncated)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if failed/timeout",
    )
    used_admin_client: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="Whether get_admin_client() was used",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="When this execution occurred (UTC)",
    )

    def __repr__(self) -> str:
        return (
            f"<FunctionExecution(id={self.id}, function_id={self.function_id}, "
            f"status={self.status})>"
        )


class FunctionSecretModel(Base):
    """Write-only encrypted secrets injected into function process env."""

    __tablename__ = "function_secrets"
    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_function_secrets_account_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Secret ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to accounts table",
    )
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Environment variable name",
    )
    value_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Fernet-encrypted secret value",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<FunctionSecret(id={self.id}, name={self.name!r})>"
