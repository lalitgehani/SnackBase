"""Integration tests: real SQLite encryption-state migration via API.

Drives CollectionService.migrate_field_encryption through the superadmin
collections endpoint and asserts DB ciphertext/plaintext without reimplementing
the migration logic.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.infrastructure.security.encryption import (
    REDACTION_PLACEHOLDER,
    EncryptionService,
)

COLLECTION = "enc_migrate_col"
FIELD = "api_token"


async def _open_collection(client: AsyncClient, headers: dict[str, str]) -> str:
    """Create collection with unencrypted secret-like field; return collection id."""
    resp = await client.post(
        "/api/v1/collections",
        headers=headers,
        json={
            "name": COLLECTION,
            "schema": [
                {"name": "label", "type": "text", "required": True},
                {"name": FIELD, "type": "text"},
            ],
        },
    )
    assert resp.status_code in (200, 201), resp.text
    collection_id = resp.json()["id"]
    await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        headers=headers,
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
    )
    return collection_id


@pytest.mark.asyncio
async def test_enable_encryption_converts_existing_rows_via_api(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = await _open_collection(client, headers)

    # Seed plaintext records
    secrets = ["secret-alpha", "secret-beta", ""]
    ids: list[str] = []
    for i, s in enumerate(secrets):
        r = await client.post(
            f"/api/v1/records/{COLLECTION}",
            headers=headers,
            json={"label": f"r{i}", "api_token": s},
        )
        assert r.status_code == 201, r.text
        # Before encryption, normal API returns plaintext
        assert r.json()["api_token"] == s
        ids.append(r.json()["id"])

    # Null secret
    rnull = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "nullish", "api_token": None},
    )
    assert rnull.status_code == 201, rnull.text
    null_id = rnull.json()["id"]

    table = TableBuilder.generate_table_name(COLLECTION)
    before = (
        await db_session.execute(
            text(f'SELECT id, api_token FROM "{table}" ORDER BY label')
        )
    ).fetchall()
    plain_by_id = {row[0]: row[1] for row in before}
    assert plain_by_id[ids[0]] == "secret-alpha"

    # Enable encryption via dedicated migration API (not plain schema PUT)
    mig = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": True},
    )
    assert mig.status_code == 200, mig.text
    body = mig.json()
    assert body["status"] == "ok"
    assert body["encrypted"] is True
    assert body["rows_converted"] >= 3  # two non-empty + empty string
    assert "secret-alpha" not in mig.text  # no values in response

    # DB holds ciphertext ≠ plaintext
    after = (
        await db_session.execute(
            text(f'SELECT id, api_token FROM "{table}" WHERE id = :id'),
            {"id": ids[0]},
        )
    ).one()
    assert after[1] != "secret-alpha"
    assert after[1] is not None
    enc = EncryptionService(get_settings().encryption_key)
    assert enc.decrypt(after[1]) == "secret-alpha"

    # Null remains null
    null_row = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": null_id},
        )
    ).scalar_one()
    assert null_row is None

    # Normal API redacts
    got = await client.get(
        f"/api/v1/records/{COLLECTION}/{ids[0]}", headers=headers
    )
    assert got.status_code == 200
    assert got.json()["api_token"] == REDACTION_PLACEHOLDER
    assert "secret-alpha" not in got.text

    # Schema flag persisted
    col = await client.get(f"/api/v1/collections/{collection_id}", headers=headers)
    assert col.status_code == 200
    fields = col.json().get("schema") or col.json().get("fields")
    token_field = next(f for f in fields if f["name"] == FIELD)
    assert token_field.get("encrypted") is True


@pytest.mark.asyncio
async def test_plain_schema_update_cannot_toggle_encryption(
    client: AsyncClient,
    superadmin_token: str,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = await _open_collection(client, headers)

    # Try to flip encrypted via ordinary PUT schema update
    bad = await client.put(
        f"/api/v1/collections/{collection_id}",
        headers=headers,
        json={
            "schema": [
                {"name": "label", "type": "text", "required": True},
                {"name": FIELD, "type": "text", "encrypted": True},
            ]
        },
    )
    assert bad.status_code == 400, bad.text
    assert "migration" in bad.text.lower() or "encryption" in bad.text.lower()


@pytest.mark.asyncio
async def test_disable_encryption_restores_plaintext(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = await _open_collection(client, headers)

    create = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "restore", "api_token": "restore-me"},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    # Enable
    en = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": True},
    )
    assert en.status_code == 200, en.text

    # Disable (explicit authorization for reverse migration)
    dis = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": False},
    )
    assert dis.status_code == 200, dis.text
    assert dis.json()["encrypted"] is False

    table = TableBuilder.generate_table_name(COLLECTION)
    val = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": rid},
        )
    ).scalar_one()
    assert val == "restore-me"

    got = await client.get(f"/api/v1/records/{COLLECTION}/{rid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["api_token"] == "restore-me"


@pytest.mark.asyncio
async def test_account_scoped_migration_refuses_schema_flip(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    """account_id must not flip encrypted while other tenants still hold plaintext.

    F4.1: refuse schema change when conversion would leave mixed state.
    """
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = await _open_collection(client, headers)

    r1 = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "sys", "api_token": "system-secret"},
    )
    assert r1.status_code == 201, r1.text
    sys_id = r1.json()["id"]
    sys_account = r1.json()["account_id"]

    other_account = "00000000-0000-0000-0000-000000000099"
    await db_session.execute(
        text(
            "INSERT OR IGNORE INTO accounts (id, account_code, name, slug, created_at, updated_at) "
            "VALUES (:id, 'OT0099', 'Other', 'other-acc', datetime('now'), datetime('now'))"
        ),
        {"id": other_account},
    )
    await db_session.commit()

    table = TableBuilder.generate_table_name(COLLECTION)
    other_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    await db_session.execute(
        text(
            f'INSERT INTO "{table}" '
            f"(id, account_id, label, api_token, created_at, updated_at, created_by, updated_by) "
            f"VALUES (:id, :acc, 'other', 'other-secret', datetime('now'), datetime('now'), "
            f"'superadmin', 'superadmin')"
        ),
        {"id": other_id, "acc": other_account},
    )
    await db_session.commit()

    # Scoped account_id must be rejected (would leave mixed plaintext/ciphertext)
    mig = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": True, "account_id": sys_account},
    )
    assert mig.status_code == 400, mig.text
    assert "account_id" in mig.text.lower() or "all accounts" in mig.text.lower()

    # Schema must remain unencrypted
    col = await client.get(f"/api/v1/collections/{collection_id}", headers=headers)
    fields = col.json().get("schema") or col.json().get("fields")
    token_field = next(f for f in fields if f["name"] == FIELD)
    assert token_field.get("encrypted") in (False, None)

    # No rows converted under a flipped flag — both still plaintext at rest
    sys_val = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": sys_id},
        )
    ).scalar_one()
    other_val = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": other_id},
        )
    ).scalar_one()
    assert sys_val == "system-secret"
    assert other_val == "other-secret"

    # Full migration (no account_id) converts every tenant then flips schema
    full = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": True},
    )
    assert full.status_code == 200, full.text
    assert full.json()["encrypted"] is True

    sys_after = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": sys_id},
        )
    ).scalar_one()
    other_after = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'),
            {"id": other_id},
        )
    ).scalar_one()
    assert sys_after != "system-secret"
    assert other_after != "other-secret"
    assert "system-secret" not in str(sys_after)
    assert "other-secret" not in str(other_after)


@pytest.mark.asyncio
async def test_migration_failure_leaves_schema_unencrypted(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """If conversion fails mid-way, schema encrypted flag must not flip."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = await _open_collection(client, headers)

    create = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "f", "api_token": "will-fail"},
    )
    assert create.status_code == 201, create.text

    # Force conversion failure by patching encrypt_value_for_field
    from snackbase.domain.services import encryption_migration_service as ems

    def boom(*_a, **_k):
        raise ValueError("injected failure")

    monkeypatch.setattr(ems, "encrypt_value_for_field", boom)

    mig = await client.post(
        f"/api/v1/collections/{collection_id}/fields/{FIELD}/encryption",
        headers=headers,
        json={"enable": True},
    )
    assert mig.status_code == 400, mig.text

    col = await client.get(f"/api/v1/collections/{collection_id}", headers=headers)
    fields = col.json().get("schema") or col.json().get("fields")
    token_field = next(f for f in fields if f["name"] == FIELD)
    assert token_field.get("encrypted") in (False, None)
