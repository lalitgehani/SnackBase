"""add_files_upload_registry

Revision ID: 20260812_files
Revises: 20260809_lockout
Create Date: 2026-08-12 00:00:00.000000

Registers every uploaded object (VAPT M-04). Downloads used to be authorized by
account prefix alone, which made a file path a bearer token for the file — and
paths are not secret. This table records who uploaded what, so a download can
be authorized against a claim rather than against knowledge of the path.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_files"
down_revision: str | Sequence[str] | None = "20260809_lockout"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), nullable=False, comment="File ID (UUID)"),
        sa.Column(
            "account_id",
            sa.String(length=36),
            nullable=False,
            comment="Owning account ID",
        ),
        sa.Column(
            "path",
            sa.String(length=512),
            nullable=False,
            comment="Storage path, e.g. {account_id}/{uuid}.{ext}",
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
            comment="Original filename supplied by the uploader",
        ),
        sa.Column(
            "mime_type",
            sa.String(length=255),
            nullable=False,
            comment="Content-derived MIME type",
        ),
        sa.Column("size", sa.BigInteger(), nullable=False, comment="File size in bytes"),
        sa.Column(
            "uploaded_by",
            sa.String(length=36),
            nullable=False,
            comment="ID of the user who uploaded the file",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_files_account_id"), ["account_id"], unique=False
        )
        batch_op.create_index("ix_files_account_path", ["account_id", "path"], unique=False)
        batch_op.create_index(batch_op.f("ix_files_path"), ["path"], unique=True)
        batch_op.create_index(
            batch_op.f("ix_files_uploaded_by"), ["uploaded_by"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_files_uploaded_by"))
        batch_op.drop_index(batch_op.f("ix_files_path"))
        batch_op.drop_index("ix_files_account_path")
        batch_op.drop_index(batch_op.f("ix_files_account_id"))

    op.drop_table("files")
