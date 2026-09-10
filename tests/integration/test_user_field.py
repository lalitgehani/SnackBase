"""Integration tests for the ``user`` field type."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

COLLECTION = "user_field_tasks"


async def _open_rules(client: AsyncClient, token: str, collection: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.put(
        f"/api/v1/collections/{collection}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


@pytest.fixture
async def user_collection(client: AsyncClient, superadmin_token: str):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/collections",
        json={
            "name": COLLECTION,
            "label": COLLECTION,
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "owner", "type": "user"},
            ],
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    await _open_rules(client, superadmin_token, COLLECTION)
    return COLLECTION


@pytest.mark.asyncio
async def test_create_user_field_collection_succeeds(
    client: AsyncClient, superadmin_token: str
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/collections",
        json={
            "name": "user_field_ok",
            "schema": [{"name": "owner", "type": "user"}],
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text


@pytest.mark.asyncio
async def test_user_field_cascade_rejected(client: AsyncClient, superadmin_token: str):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post(
        "/api/v1/collections",
        json={
            "name": "user_field_cascade",
            "schema": [{"name": "owner", "type": "user", "on_delete": "cascade"}],
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "owner" in response.text


@pytest.mark.asyncio
async def test_write_own_user_id(
    client: AsyncClient,
    superadmin_token: str,
    regular_user_token: str,
    user_collection: str,
):
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await client.post(
        f"/api/v1/records/{user_collection}",
        json={"title": "mine", "owner": "regular_user"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["owner"] == "regular_user"


@pytest.mark.asyncio
async def test_write_missing_user_id_is_invalid_reference(
    client: AsyncClient,
    regular_user_token: str,
    user_collection: str,
):
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    missing = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/records/{user_collection}",
        json={"title": "ghost", "owner": missing},
        headers=headers,
    )
    assert response.status_code == 400
    body = response.json()
    codes = [item.get("code") for item in body.get("details", [])]
    assert "invalid_reference" in codes


@pytest.mark.asyncio
async def test_write_cross_account_user_id_is_invalid_reference(
    client: AsyncClient,
    db_session: AsyncSession,
    regular_user_token: str,
    user_collection: str,
):
    other_account = AccountModel(
        id="00000000-0000-0000-0000-000000000099",
        account_code="XA0099",
        name="Other Account",
        slug="other-acc",
    )
    db_session.add(other_account)
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    other_user = UserModel(
        id="other_account_user",
        email="other@snackbase.com",
        account_id=other_account.id,
        password_hash="hashed_secret",
        role=user_role,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = await client.post(
        f"/api/v1/records/{user_collection}",
        json={"title": "cross", "owner": "other_account_user"},
        headers=headers,
    )
    assert response.status_code == 400
    body = response.json()
    codes = [item.get("code") for item in body.get("details", [])]
    assert "invalid_reference" in codes


@pytest.mark.asyncio
async def test_expand_user_field_redacted_projection(
    client: AsyncClient,
    db_session: AsyncSession,
    regular_user_token: str,
    user_collection: str,
):
    user = await db_session.get(UserModel, "regular_user")
    assert user is not None
    user.profile_data = {
        "first_name": "Reg",
        "last_name": "User",
        "avatar_url": "https://example.com/reg.png",
    }
    await db_session.commit()

    headers = {"Authorization": f"Bearer {regular_user_token}"}
    created = await client.post(
        f"/api/v1/records/{user_collection}",
        json={"title": "expand-me", "owner": "regular_user"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/records/{user_collection}/{record_id}",
        params={"expand": "owner"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    owner = response.json()["owner"]
    assert set(owner.keys()) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "avatar_url",
    }
    assert owner["id"] == "regular_user"
    assert owner["email"] == "user@snackbase.com"
    assert owner["first_name"] == "Reg"
    assert owner["last_name"] == "User"
    assert owner["avatar_url"] == "https://example.com/reg.png"
    for forbidden in ("password_hash", "role_id", "auth_provider", "external_id"):
        assert forbidden not in owner


@pytest.mark.asyncio
async def test_user_field_rule_filters_by_auth_id(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
    regular_user_token: str,
    user_collection: str,
):
    headers_admin = {"Authorization": f"Bearer {superadmin_token}"}
    locked = await client.put(
        f"/api/v1/collections/{user_collection}/rules",
        json={
            "list_rule": "owner = @request.auth.id",
            "view_rule": "owner = @request.auth.id",
            "create_rule": "",
            "update_rule": "owner = @request.auth.id",
            "delete_rule": "owner = @request.auth.id",
        },
        headers=headers_admin,
    )
    assert locked.status_code == 200, locked.text

    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    other = UserModel(
        id="same_account_other",
        email="other-same@snackbase.com",
        account_id="00000000-0000-0000-0000-000000000001",
        password_hash="hashed_secret",
        role=user_role,
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()

    from snackbase.infrastructure.auth.jwt_service import jwt_service

    other_token = jwt_service.create_access_token(
        user_id=other.id,
        account_id=other.account_id,
        email=other.email,
        role="user",
    )

    mine = await client.post(
        f"/api/v1/records/{user_collection}",
        json={"title": "private", "owner": "regular_user"},
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert mine.status_code == 201, mine.text

    listed = await client.get(
        f"/api/v1/records/{user_collection}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert listed.status_code == 200
    items = listed.json().get("items") or listed.json().get("data") or []
    assert all(item.get("owner") != "regular_user" for item in items)
