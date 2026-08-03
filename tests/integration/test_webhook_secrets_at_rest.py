"""Integration tests for webhook secret encryption at rest."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.webhook import WebhookModel
from snackbase.infrastructure.webhooks.webhook_service import (
    resolve_webhook_signing_secret,
    sign_payload,
)


@pytest.mark.asyncio
async def test_create_webhook_stores_ciphertext(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Ensure a collection exists for the webhook
    await client.post(
        "/api/v1/collections",
        headers=headers,
        json={
            "name": "wh_enc_col",
            "schema": [{"name": "title", "type": "text"}],
        },
    )
    await client.put(
        "/api/v1/collections/wh_enc_col/rules",
        headers=headers,
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
    )

    plain_secret = "one-time-visible-secret-xyz"
    resp = await client.post(
        "/api/v1/webhooks",
        headers=headers,
        json={
            "url": "https://example.com/hooks/snackbase",
            "collection": "wh_enc_col",
            "events": ["create"],
            "secret": plain_secret,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["secret"] == plain_secret  # one-time plaintext

    # List/get must not include secret
    listed = await client.get("/api/v1/webhooks", headers=headers)
    assert listed.status_code == 200
    assert "one-time-visible-secret" not in listed.text
    assert "secret" not in listed.json()["items"][0]

    # DB stores ciphertext
    wh_id = body["id"]
    row = (
        await db_session.execute(
            select(WebhookModel).where(WebhookModel.id == wh_id)
        )
    ).scalar_one()
    assert row.secret != plain_secret
    assert resolve_webhook_signing_secret(row.secret) == plain_secret

    # Signing still works with resolved secret
    body_bytes = b'{"event":"create"}'
    assert sign_payload(
        resolve_webhook_signing_secret(row.secret), body_bytes
    ) == sign_payload(plain_secret, body_bytes)
