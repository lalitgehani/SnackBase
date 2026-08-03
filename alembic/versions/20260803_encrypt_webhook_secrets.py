"""Encrypt existing webhook signing secrets and widen secret column.

Revision ID: 20260803_wh_secrets
Revises: 20260725_no_default_regions
Create Date: 2026-08-03
"""

from __future__ import annotations

import base64
import hashlib
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet, InvalidToken

# revision identifiers, used by Alembic.
revision: str = "20260803_wh_secrets"
down_revision: str | None = "20260725_no_default_regions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_KEY = "change-me-in-production-use-openssl-rand-hex-32"


def _fernet() -> Fernet:
    secret_key = os.environ.get("SNACKBASE_ENCRYPTION_KEY", DEFAULT_KEY)
    h = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(h))


def _looks_encrypted(value: str, f: Fernet) -> bool:
    try:
        f.decrypt(value.encode("utf-8"))
        return True
    except (InvalidToken, ValueError, TypeError):
        return False


def upgrade() -> None:
    """Widen secret column and encrypt any remaining plaintext secrets."""
    conn = op.get_bind()
    # Widen column for Fernet ciphertext (dialect-aware)
    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.alter_column(
            "webhooks",
            "secret",
            existing_type=sa.String(length=100),
            type_=sa.Text(),
            existing_nullable=False,
        )
    else:
        # SQLite: recreate is heavy; TEXT affinity already accepts long strings
        # after type change via batch mode
        with op.batch_alter_table("webhooks") as batch_op:
            batch_op.alter_column(
                "secret",
                existing_type=sa.String(length=100),
                type_=sa.Text(),
                existing_nullable=False,
            )

    f = _fernet()
    rows = conn.execute(sa.text("SELECT id, secret FROM webhooks")).fetchall()
    for row in rows:
        webhook_id, secret = row[0], row[1]
        if secret is None or secret == "":
            continue
        if _looks_encrypted(secret, f):
            continue
        ciphertext = f.encrypt(secret.encode("utf-8")).decode("utf-8")
        conn.execute(
            sa.text("UPDATE webhooks SET secret = :s WHERE id = :id"),
            {"s": ciphertext, "id": webhook_id},
        )


def downgrade() -> None:
    """Decrypt secrets back to plaintext and shrink column (best-effort)."""
    conn = op.get_bind()
    f = _fernet()
    rows = conn.execute(sa.text("SELECT id, secret FROM webhooks")).fetchall()
    for row in rows:
        webhook_id, secret = row[0], row[1]
        if secret is None:
            continue
        try:
            plaintext = f.decrypt(secret.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError):
            continue
        conn.execute(
            sa.text("UPDATE webhooks SET secret = :s WHERE id = :id"),
            {"s": plaintext, "id": webhook_id},
        )

    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.alter_column(
            "webhooks",
            "secret",
            existing_type=sa.Text(),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("webhooks") as batch_op:
            batch_op.alter_column(
                "secret",
                existing_type=sa.Text(),
                type_=sa.String(length=100),
                existing_nullable=False,
            )
