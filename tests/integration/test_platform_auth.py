"""Integration tests for platform authentication (F2.3, F2.4, F2.6)."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy import func, select
from tests.helpers.platform_tokens import (
    build_jwks,
    generate_rsa_keypair,
    mint_platform_token,
    platform_settings_env,
)

from snackbase.core.config import get_settings
from snackbase.infrastructure.auth.platform_jwks import reset_platform_jwks_client
from snackbase.infrastructure.persistence.models import AccountModel, UserModel
from snackbase.infrastructure.persistence.table_builder import TableBuilder

pytestmark = pytest.mark.enable_audit_hooks


@pytest.fixture(autouse=True)
def _platform_env(monkeypatch):
    for key, value in platform_settings_env().items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    reset_platform_jwks_client()
    yield
    get_settings.cache_clear()
    reset_platform_jwks_client()


@pytest.fixture
def platform_keys():
    return generate_rsa_keypair()


@pytest.fixture
def jwks_mock(platform_keys):
    _, public_key = platform_keys

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = build_jwks(public_key)

    with patch(
        "snackbase.infrastructure.auth.platform_jwks.httpx.get",
        return_value=mock_response,
    ):
        yield


@pytest.fixture
async def single_tenant_account(db_session):
    account = AccountModel(
        id="00000000-0000-0000-0000-00000000aa01",
        account_code="PA0001",
        name="Platform App",
        slug="platform-app",
    )
    db_session.add(account)
    await db_session.commit()
    return account


def _platform_token(private_key, **kwargs) -> str:
    return mint_platform_token(private_key, **kwargs)


async def _create_collection_with_public_rules(
    db_session, collection_id: str, collection_name: str, schema: list
) -> None:
    from snackbase.infrastructure.persistence.models import CollectionModel
    from snackbase.infrastructure.persistence.models.collection_rule import CollectionRuleModel

    collection = CollectionModel(
        id=collection_id,
        name=collection_name,
        schema=json.dumps(schema),
    )
    db_session.add(collection)
    db_session.add(
        CollectionRuleModel(
            id=f"rule-{collection_id}",
            collection_id=collection_id,
            list_rule="",
            view_rule="",
            create_rule="",
            update_rule="",
            delete_rule="",
        )
    )
    await TableBuilder.create_table(db_session.bind, collection_name, schema)
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_and_user_roles_authenticate(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    for role, sub, email in [
        ("admin", "admin-sub", "admin@platform.example.com"),
        ("user", "user-sub", "user@platform.example.com"),
    ]:
        token = _platform_token(private_key, role=role, sub=sub, email=email)
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_same_sub_produces_one_user_row(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    token = _platform_token(private_key, sub="stable-sub", email="stable@example.com")

    for _ in range(2):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    count = (
        await db_session.execute(
            select(func.count()).select_from(UserModel).where(UserModel.id == "stable-sub")
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_jit_user_cannot_password_login(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="jit-user",
        email="jit@example.com",
        role="user",
    )
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == status.HTTP_200_OK

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "jit@example.com",
            "password": "any-password",
            "account": "platform-app",
        },
    )
    assert login.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_platform_token_audit_auth_method(
    client, db_session, superadmin_token, single_tenant_account, platform_keys, jwks_mock
):
    collection_name = "platform_audit_col"
    schema = [{"name": "title", "type": "text"}]
    await _create_collection_with_public_rules(
        db_session, "col-platform-audit", collection_name, schema
    )

    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="audit-user",
        email="audit@example.com",
        role="admin",
    )

    create = await client.post(
        f"/api/v1/records/{collection_name}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "from platform"},
    )
    assert create.status_code == status.HTTP_201_CREATED

    logs = await client.get(
        "/api/v1/audit-logs/",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        params={"auth_method": "platform"},
    )
    assert logs.status_code == status.HTTP_200_OK
    items = logs.json()["items"]
    assert any(item["user_email"] == "audit@example.com" for item in items)
    assert all(
        "token" not in str(item.get("extra_metadata", {})).lower()
        for item in items
    )


@pytest.mark.asyncio
async def test_platform_admin_can_list_collections(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="studio-admin",
        email="studio-admin@platform.example.com",
        role="admin",
    )
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK, response.text


@pytest.mark.asyncio
async def test_platform_user_cannot_list_collections(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="studio-user",
        email="studio-user@platform.example.com",
        role="user",
    )
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_local_jwt_audit_auth_method_not_platform(
    client, db_session, superadmin_token, single_tenant_account, platform_keys, jwks_mock
):
    from snackbase.infrastructure.persistence.models import CollectionModel

    collection_name = "local_audit_col"
    schema = [{"name": "title", "type": "text"}]
    collection = CollectionModel(
        id="col-local-audit",
        name=collection_name,
        schema=json.dumps(schema),
    )
    db_session.add(collection)
    await TableBuilder.create_table(db_session.bind, collection_name, schema)
    await db_session.commit()

    create = await client.post(
        f"/api/v1/records/{collection_name}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"title": "from local jwt"},
    )
    assert create.status_code == status.HTTP_201_CREATED

    logs = await client.get(
        "/api/v1/audit-logs/",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        params={"auth_method": "jwt"},
    )
    assert logs.status_code == status.HTTP_200_OK
    assert logs.json()["total"] >= 1
    assert all(
        item.get("extra_metadata", {}).get("auth_method") == "jwt"
        for item in logs.json()["items"]
    )


@pytest.mark.asyncio
async def test_cross_account_record_access_denied(
    client, db_session, single_tenant_account, platform_keys, jwks_mock
):
    other_account = AccountModel(
        id="00000000-0000-0000-0000-00000000bb02",
        account_code="OB0002",
        name="Other",
        slug="other-account",
    )
    db_session.add(other_account)
    await db_session.commit()

    private_key, _ = platform_keys
    token = _platform_token(private_key, sub="isolated-user", role="admin")

    response = await client.get(
        f"/api/v1/accounts/{other_account.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    }


@pytest.mark.asyncio
async def test_realtime_authenticate_accepts_platform_token(
    db_session, single_tenant_account, platform_keys, jwks_mock
):
    from snackbase.infrastructure.auth.token_types import TokenType
    from snackbase.infrastructure.realtime.realtime_auth import authenticate_realtime

    private_key, _ = platform_keys
    token = _platform_token(private_key, sub="rt-user", role="user", email="rt@example.com")

    user = await authenticate_realtime(token, session=db_session)
    assert user.token_type == TokenType.PLATFORM
    assert user.email == "rt@example.com"


@pytest.mark.asyncio
async def test_expired_platform_token_rejected_at_realtime_connect(
    db_session, single_tenant_account, platform_keys, jwks_mock
):
    from fastapi import HTTPException

    from snackbase.infrastructure.realtime.realtime_auth import authenticate_realtime

    private_key, _ = platform_keys
    now = int(time.time())
    token = _platform_token(
        private_key,
        sub="exp-user",
        iat=now - 400,
        exp=now - 60,
    )

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_realtime(token, session=db_session)
    assert exc_info.value.status_code == 401
