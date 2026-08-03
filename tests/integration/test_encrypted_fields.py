"""Integration tests for encrypted collection fields and secret reveal."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.api_key_service import api_key_service
from snackbase.infrastructure.persistence.models import UserModel
from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.infrastructure.security.encryption import REDACTION_PLACEHOLDER
from snackbase.infrastructure.security.scopes import SCOPE_RECORDS_SECRETS_READ

COLLECTION = "enc_creds_col"
SCHEMA = [
    {"name": "label", "type": "text", "required": True},
    {"name": "api_token", "type": "text", "encrypted": True},
    {"name": "meta", "type": "json", "encrypted": True},
]


@pytest.fixture(autouse=True)
async def setup_collection(client: AsyncClient, superadmin_token: str):
    """Create collection with encrypted fields and open rules."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "schema": SCHEMA},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )
    yield


@pytest.mark.asyncio
async def test_create_stores_ciphertext_and_redacts_response(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    payload = {
        "label": "prod",
        "api_token": "super-secret-token-value",
        "meta": {"region": "us", "key": "k1"},
    }
    resp = await client.post(
        f"/api/v1/records/{COLLECTION}", headers=headers, json=payload
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body.get("api_token") == REDACTION_PLACEHOLDER
    assert body.get("meta") == REDACTION_PLACEHOLDER
    assert body.get("label") == "prod"
    assert "super-secret-token-value" not in resp.text
    assert "k1" not in resp.text

    record_id = body["id"]
    table = TableBuilder.generate_table_name(COLLECTION)
    result = await db_session.execute(
        text(f'SELECT api_token, meta FROM "{table}" WHERE id = :id'),
        {"id": record_id},
    )
    row = result.one()
    assert row[0] != "super-secret-token-value"
    assert row[0] is not None
    assert "super-secret-token-value" not in str(row[1])


@pytest.mark.asyncio
async def test_get_list_redact_encrypted_fields(
    client: AsyncClient,
    superadmin_token: str,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    create = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "x", "api_token": "hidden-token", "meta": {"a": 1}},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    got = await client.get(f"/api/v1/records/{COLLECTION}/{rid}", headers=headers)
    assert got.status_code == 200
    assert got.json()["api_token"] == REDACTION_PLACEHOLDER
    assert "hidden-token" not in got.text

    listed = await client.get(f"/api/v1/records/{COLLECTION}", headers=headers)
    assert listed.status_code == 200
    assert "hidden-token" not in listed.text


@pytest.mark.asyncio
async def test_patch_placeholder_and_omit_preserve_secret(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    create = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "a", "api_token": "keep-me-secret", "meta": None},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]
    table = TableBuilder.generate_table_name(COLLECTION)
    before = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'), {"id": rid}
        )
    ).scalar_one()

    # Placeholder must not overwrite
    patch = await client.patch(
        f"/api/v1/records/{COLLECTION}/{rid}",
        headers=headers,
        json={"label": "b", "api_token": REDACTION_PLACEHOLDER},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["label"] == "b"
    assert patch.json()["api_token"] == REDACTION_PLACEHOLDER
    after_placeholder = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'), {"id": rid}
        )
    ).scalar_one()
    assert after_placeholder == before

    # Omission preserves
    patch2 = await client.patch(
        f"/api/v1/records/{COLLECTION}/{rid}",
        headers=headers,
        json={"label": "c"},
    )
    assert patch2.status_code == 200
    after_omit = (
        await db_session.execute(
            text(f'SELECT api_token FROM "{table}" WHERE id = :id'), {"id": rid}
        )
    ).scalar_one()
    assert after_omit == before


@pytest.mark.asyncio
async def test_cannot_sort_or_filter_encrypted_field(
    client: AsyncClient,
    superadmin_token: str,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "z", "api_token": "t", "meta": None},
    )
    bad_sort = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        params={"sort": "api_token"},
    )
    assert bad_sort.status_code == 400

    bad_filter = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        params={"filter": 'api_token = "t"'},
    )
    assert bad_filter.status_code == 400


@pytest.mark.asyncio
async def test_secret_reveal_scope_and_success(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    create = await client.post(
        f"/api/v1/records/{COLLECTION}",
        headers=headers,
        json={"label": "r", "api_token": "reveal-me", "meta": {"a": 1}},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    # JWT cannot reveal even as superadmin
    denied = await client.get(
        f"/api/v1/records/{COLLECTION}/{rid}/secrets",
        headers=headers,
    )
    assert denied.status_code == 403

    # Non-encrypted field rejected
    # First get a scoped key
    user = (
        await db_session.execute(select(UserModel).where(UserModel.id == "superadmin"))
    ).scalar_one()
    plaintext, _ = await api_key_service.create_api_key(
        session=db_session,
        user_id=user.id,
        email=user.email,
        account_id=user.account_id,
        role="admin",
        name="Secrets Key",
        scopes=[SCOPE_RECORDS_SECRETS_READ],
    )
    await db_session.commit()
    key_headers = {"X-API-Key": plaintext}

    bad_field = await client.get(
        f"/api/v1/records/{COLLECTION}/{rid}/secrets",
        headers=key_headers,
        params={"fields": "label"},
    )
    assert bad_field.status_code == 400

    ok = await client.get(
        f"/api/v1/records/{COLLECTION}/{rid}/secrets",
        headers=key_headers,
        params={"fields": "api_token,meta"},
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()["data"]
    assert data["api_token"] == "reveal-me"
    assert data["meta"] == {"a": 1}

    # Missing scope
    plain2, _ = await api_key_service.create_api_key(
        session=db_session,
        user_id=user.id,
        email=user.email,
        account_id=user.account_id,
        role="admin",
        name="No Scope",
        scopes=[],
    )
    await db_session.commit()
    noscope = await client.get(
        f"/api/v1/records/{COLLECTION}/{rid}/secrets",
        headers={"X-API-Key": plain2},
    )
    assert noscope.status_code == 403

    # Cross-account / missing record
    missing = await client.get(
        f"/api/v1/records/{COLLECTION}/00000000-0000-0000-0000-000000000099/secrets",
        headers=key_headers,
        params={"fields": "api_token"},
    )
    assert missing.status_code == 404
