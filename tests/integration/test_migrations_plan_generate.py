"""Integration tests for POST /migrations/plan and /migrations/generate."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.migration_service import dynamic_migrations_dir

COLLECTION = "mig_plan_items"


async def _create_collection(client: AsyncClient, token: str, name: str, schema: list) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/collections",
        json={"name": name, "schema": schema},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    await client.put(
        f"/api/v1/collections/{name}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )
    return response.json()


@pytest.mark.asyncio
async def test_plan_unchanged_schema_is_empty(
    client: AsyncClient, superadmin_token: str
):
    schema = [{"name": "title", "type": "text"}]
    await _create_collection(client, superadmin_token, "mig_unchanged", schema)
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/migrations/plan",
        json={"collections": [{"name": "mig_unchanged", "schema": schema}]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["added"] == []
    assert body["removed"] == []
    assert body["changed"] == []


@pytest.mark.asyncio
async def test_plan_nullable_add_is_not_destructive(
    client: AsyncClient, superadmin_token: str
):
    schema = [{"name": "title", "type": "text"}]
    await _create_collection(client, superadmin_token, "mig_add_field", schema)
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    declared = [
        {"name": "title", "type": "text"},
        {"name": "subtitle", "type": "text"},
    ]
    response = await client.post(
        "/api/v1/migrations/plan",
        json={"collections": [{"name": "mig_add_field", "schema": declared}]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["added"]) == 1
    assert body["added"][0]["field"] == "subtitle"
    assert body["added"][0]["destructive"] is False


@pytest.mark.asyncio
async def test_plan_reference_to_text_is_destructive(
    client: AsyncClient, superadmin_token: str
):
    await _create_collection(
        client,
        superadmin_token,
        "mig_ref_targets",
        [{"name": "label", "type": "text"}],
    )
    await _create_collection(
        client,
        superadmin_token,
        "mig_ref_change",
        [
            {
                "name": "target",
                "type": "reference",
                "collection": "mig_ref_targets",
                "on_delete": "set_null",
            }
        ],
    )
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/migrations/plan",
        json={
            "collections": [
                {"name": "mig_ref_targets", "schema": [{"name": "label", "type": "text"}]},
                {"name": "mig_ref_change", "schema": [{"name": "target", "type": "text"}]},
            ]
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    changed = response.json()["changed"]
    assert any(
        item["field"] == "target"
        and item["from"] == "reference"
        and item["to"] == "text"
        and item["destructive"] is True
        for item in changed
    )


@pytest.mark.asyncio
async def test_generate_destructive_without_confirm_writes_nothing(
    client: AsyncClient, superadmin_token: str
):
    schema = [{"name": "amount", "type": "number"}]
    await _create_collection(client, superadmin_token, "mig_no_confirm", schema)
    before = set(dynamic_migrations_dir().glob("*.py"))
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/migrations/generate",
        json={
            "collections": [
                {"name": "mig_no_confirm", "schema": [{"name": "amount", "type": "text"}]}
            ],
            "confirm": False,
        },
        headers=headers,
    )
    assert response.status_code == 409, response.text
    assert response.json()["plan"]["changed"]
    after = set(dynamic_migrations_dir().glob("*.py"))
    assert after == before


@pytest.mark.asyncio
async def test_generate_with_confirm_writes_one_revision_and_applies(
    client: AsyncClient,
    superadmin_token: str,
    db_session: AsyncSession,
):
    schema = [{"name": "amount", "type": "number"}]
    await _create_collection(client, superadmin_token, "mig_confirm", schema)
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    for i in range(100):
        created = await client.post(
            "/api/v1/records/mig_confirm",
            json={"amount": i},
            headers=headers,
        )
        assert created.status_code == 201, created.text

    before = set(dynamic_migrations_dir().glob("*.py"))
    response = await client.post(
        "/api/v1/migrations/generate",
        json={
            "collections": [
                {"name": "mig_confirm", "schema": [{"name": "amount", "type": "text"}]}
            ],
            "confirm": True,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    rev_id = body["revision"]
    assert rev_id
    after = set(dynamic_migrations_dir().glob("*.py"))
    assert len(after - before) == 1

    await db_session.commit()
    rows = (
        await db_session.execute(text("SELECT version_num FROM alembic_version"))
    ).fetchall()
    assert rev_id in {row[0] for row in rows}

    listed = await client.get(
        "/api/v1/records/mig_confirm",
        params={"limit": 100},
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 100


@pytest.mark.asyncio
async def test_generate_non_superadmin_forbidden(
    client: AsyncClient, regular_user_token: str
):
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    plan = await client.post(
        "/api/v1/migrations/plan",
        json={"collections": []},
        headers=headers,
    )
    assert plan.status_code == 403
    generate = await client.post(
        "/api/v1/migrations/generate",
        json={"collections": [], "confirm": True},
        headers=headers,
    )
    assert generate.status_code == 403


@pytest.mark.asyncio
async def test_put_collection_still_rejects_in_place_type_change(
    client: AsyncClient, superadmin_token: str
):
    created = await _create_collection(
        client,
        superadmin_token,
        "mig_put_guard",
        [{"name": "title", "type": "text"}],
    )
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    collection_id = created["id"]
    response = await client.put(
        f"/api/v1/collections/{collection_id}",
        json={
            "schema": [{"name": "title", "type": "number"}],
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "type" in response.text.lower()
