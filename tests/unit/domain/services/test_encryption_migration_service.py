"""Unit tests for collection field encryption-state migration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from snackbase.domain.services.encryption_migration_service import (
    EncryptionMigrationService,
)
from snackbase.infrastructure.security.encryption import EncryptionService


@pytest.mark.asyncio
async def test_convert_value_encrypt_decrypt_round_trip():
    enc = EncryptionService("migration-test-key")
    svc = EncryptionMigrationService(AsyncMock(), enc)

    cipher = svc._convert_value("hello", "text", enable_encryption=True)
    assert cipher != "hello"
    plain = svc._convert_value(cipher, "text", enable_encryption=False)
    assert plain == "hello"

    obj = {"a": 1, "b": "x"}
    json_cipher = svc._convert_value(obj, "json", enable_encryption=True)
    assert isinstance(json_cipher, str)
    restored = svc._convert_value(json_cipher, "json", enable_encryption=False)
    # decrypt path returns json.dumps of original
    import json

    assert json.loads(restored) == obj


@pytest.mark.asyncio
async def test_migrate_field_processes_batches_and_skips_null():
    enc = EncryptionService("migration-test-key")
    session = AsyncMock()

    batch1 = [("id-1", "secret-a"), ("id-2", None)]
    batch2: list = []
    select_calls = {"n": 0}

    async def execute_side_effect(stmt, params=None):
        sql = str(stmt)
        result = MagicMock()
        if "SELECT" in sql.upper():
            select_calls["n"] += 1
            result.fetchall = MagicMock(
                return_value=batch1 if select_calls["n"] == 1 else batch2
            )
        else:
            result.fetchall = MagicMock(return_value=[])
        return result

    session.execute = AsyncMock(side_effect=execute_side_effect)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    svc = EncryptionMigrationService(session, enc, batch_size=10)
    result = await svc.migrate_field(
        "demo",
        "api_token",
        "text",
        enable_encryption=True,
        account_id="acc-1",
    )
    assert result.success is True
    assert result.rows_processed == 2
    assert result.rows_converted == 1
    assert result.rows_skipped_null == 1
    session.commit.assert_awaited()
