"""Integration tests for InProcessClient isolation and transport."""

import socket

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.embedded import InProcessClient, SnackBaseClientError, create_client
from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel

COLLECTION = "ipc_notes"


async def _open_rules(client: AsyncClient, token: str, name: str) -> None:
    response = await client.put(
        f"/api/v1/collections/{name}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


@pytest.fixture
async def ipc_collection(client: AsyncClient, superadmin_token: str) -> str:
    response = await client.post(
        "/api/v1/collections",
        json={
            "name": COLLECTION,
            "schema": [{"name": "title", "type": "text", "required": True}],
        },
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code in (200, 201), response.text
    await _open_rules(client, superadmin_token, COLLECTION)
    return COLLECTION


async def _second_account_token(db_session: AsyncSession) -> str:
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000042",
        account_code="XA0042",
        name="Second Account",
        slug="second-acc",
    )
    db_session.add(account)
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    user = UserModel(
        id="second_account_user",
        email="second@snackbase.com",
        account_id=account.id,
        password_hash="hashed_secret",
        role=user_role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user.id,
        account_id=user.account_id,
        email=user.email,
        role="user",
    )


@pytest.mark.asyncio
async def test_inprocess_list_matches_http_shape(
    client: AsyncClient,
    regular_user_token: str,
    ipc_collection: str,
):
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    created = await client.post(
        f"/api/v1/records/{ipc_collection}",
        json={"title": "hello"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    http_list = await client.get(f"/api/v1/records/{ipc_collection}", headers=headers)
    assert http_list.status_code == 200
    http_body = http_list.json()

    ipc = InProcessClient(app, token=regular_user_token)
    ipc_body = await ipc.list(ipc_collection)
    assert {item["id"] for item in ipc_body["items"]} == {
        item["id"] for item in http_body["items"]
    }
    await ipc.aclose()


@pytest.mark.asyncio
async def test_inprocess_cross_tenant_list_empty_and_get_404(
    client: AsyncClient,
    db_session: AsyncSession,
    regular_user_token: str,
    ipc_collection: str,
):
    created = await client.post(
        f"/api/v1/records/{ipc_collection}",
        json={"title": "tenant-a"},
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]

    other_token = await _second_account_token(db_session)
    ipc = InProcessClient(app, token=other_token)
    listed = await ipc.list(ipc_collection)
    ids = {item["id"] for item in listed["items"]}
    assert record_id not in ids

    with pytest.raises(SnackBaseClientError) as exc:
        await ipc.get(ipc_collection, record_id)
    assert exc.value.status_code == 404
    await ipc.aclose()


@pytest.mark.asyncio
async def test_inprocess_issues_zero_tcp_connections(
    client: AsyncClient,
    regular_user_token: str,
    ipc_collection: str,
):
    ipc = InProcessClient(app, token=regular_user_token)
    assert isinstance(ipc._http._transport, ASGITransport)

    original = socket.socket.connect
    calls: list[object] = []

    def spy(self: socket.socket, address: object) -> None:
        calls.append(address)
        return original(self, address)

    socket.socket.connect = spy  # type: ignore[method-assign]
    try:
        await ipc.create(ipc_collection, {"title": "one"})
        await ipc.list(ipc_collection)
        await ipc.me()
    finally:
        socket.socket.connect = original  # type: ignore[method-assign]
        await ipc.aclose()

    assert calls == []


@pytest.mark.asyncio
async def test_factory_embedded_uses_inprocess() -> None:
    client = create_client(app=app, token="x")
    assert isinstance(client, InProcessClient)
    await client.aclose()
