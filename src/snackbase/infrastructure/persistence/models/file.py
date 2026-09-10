"""SQLAlchemy model for the files table.

Registers every stored object so a download can be authorized against
something other than the path itself.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from snackbase.infrastructure.persistence.database import Base


class FileModel(Base):
    """SQLAlchemy model for the files table.

    Uploads used to leave no trace outside the record that happened to
    reference them, so the only thing a download could check was that the path
    started with the caller's account. A path is not a secret — it is returned
    in record payloads, echoed in webhooks and kept in exports — so that made
    it a bearer token for the file.

    This row is what lets the download endpoint answer "who put this here, and
    which record governs it" (see `FILE-AUTHZ-*`).

    Attributes:
        id: Primary key (UUID string).
        account_id: Owning account (files never cross this boundary).
        path: Storage path as handed to clients, e.g. ``{account_id}/{uuid}.png``.
        filename: Original filename as supplied by the uploader, for display.
        mime_type: Content-derived MIME type at upload time.
        size: Size in bytes.
        uploaded_by: User who uploaded the file.
        created_at: Timestamp when the file was stored.
    """

    __tablename__ = "files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="File ID (UUID)",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning account ID",
    )
    path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True,
        index=True,
        comment="Storage path, e.g. {account_id}/{uuid}.{ext}",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename supplied by the uploader",
    )
    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Content-derived MIME type",
    )
    size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="ID of the user who uploaded the file",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (Index("ix_files_account_path", "account_id", "path"),)

    def __repr__(self) -> str:
        return f"<File(id={self.id}, path={self.path}, account_id={self.account_id})>"
