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
from snackbase.infrastructure.auth.authenticator import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.auth.platform_jwks import reset_platform_jwks_client
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel
from snackbase.infrastructure.persistence.repositories import AccountRepository
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
async def system_account(db_session):
    """The instance system account (SY0000).

    Platform principals are instance operators and resolve here, regardless of the
    instance's own tenancy. Idempotent, so it composes with conftest's
    ``superadmin_token`` fixture in either order.
    """
    from snackbase.domain.services.superadmin_service import SuperadminService

    await SuperadminService.ensure_system_account_exists(db_session)
    return await AccountRepository(db_session).get_by_id(SYSTEM_ACCOUNT_ID)


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
async def test_operator_role_authenticates_into_system_account(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """An `admin` platform principal is the instance operator: it authenticates and is
    provisioned into SY0000, on an instance that is NOT in single-tenant mode."""
    private_key, _ = platform_keys
    token = _platform_token(
        private_key, role="admin", sub="admin-sub", email="admin@platform.example.com"
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["email"] == "admin@platform.example.com"
    assert response.json()["account_id"] == SYSTEM_ACCOUNT_ID

    row = (
        await db_session.execute(select(UserModel).where(UserModel.id == "admin-sub"))
    ).scalar_one()
    assert row.account_id == SYSTEM_ACCOUNT_ID
    assert row.auth_provider == "platform"


@pytest.mark.asyncio
async def test_non_operator_role_rejected_and_creates_no_user(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """A non-admin platform role has no identity to map to: `require_superadmin` admits
    on account membership alone, so anything landing in SY0000 would be an operator.
    It must fail closed at authentication, before any row is written."""
    private_key, _ = platform_keys
    token = _platform_token(
        private_key, role="user", sub="user-sub", email="user@platform.example.com"
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    count = (
        await db_session.execute(
            select(func.count()).select_from(UserModel).where(UserModel.id == "user-sub")
        )
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_same_sub_produces_one_user_row(
    client, db_session, system_account, platform_keys, jwks_mock
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
    client, db_session, system_account, platform_keys, jwks_mock
):
    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="jit-user",
        email="jit@example.com",
        role="admin",
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
            "account": "system",
        },
    )
    assert login.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_platform_token_audit_auth_method(
    client, db_session, superadmin_token, system_account, platform_keys, jwks_mock
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
        "/api/v1/audit-logs",
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
    client, db_session, system_account, platform_keys, jwks_mock
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
async def test_platform_user_token_rejected_at_authentication(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """Rejection moved from authorization to authentication, so this is now 401 rather
    than 403 — no principal is established at all."""
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
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_local_jwt_audit_auth_method_not_platform(
    client, db_session, superadmin_token, system_account, platform_keys, jwks_mock
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
        "/api/v1/audit-logs",
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
async def test_platform_operator_reaches_all_instance_accounts(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """DELIBERATE CHANGE OF INVARIANT — do not "fix" this back to a 403/404.

    This test previously asserted that a platform principal could not read another
    account, which was correct while platform principals were provisioned into a *tenant*
    account. They are now instance operators in SY0000.

    Cloud provisions one dedicated instance per environment, so every account on this
    instance belongs to the customer operating it — those are their own application's
    end-tenants, not other customers. Reading across them is the operator's own data, and
    is exactly what a self-hosted superadmin can do. Cross-*customer* isolation is enforced
    at the control plane, which resolves an environment to its owner before minting a
    token at all.

    The isolation that still matters is asserted by
    ``test_non_operator_role_rejected_and_creates_no_user``: a non-admin never becomes an
    operator in the first place.
    """
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
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["id"] == other_account.id


@pytest.mark.asyncio
async def test_legacy_platform_user_is_migrated_to_system_account(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """Rows provisioned by the pre-operator-model code landed in the instance's tenant
    account. Without in-place reconciliation the lookup would return early and the
    operator would silently lose Studio access after upgrading."""
    tenant = AccountModel(
        id="00000000-0000-0000-0000-00000000aa01",
        account_code="PA0001",
        name="Platform App",
        slug="platform-app",
    )
    db_session.add(tenant)
    await db_session.commit()

    role_id = (
        await db_session.execute(select(RoleModel.id).where(RoleModel.name == "admin"))
    ).scalar_one()
    db_session.add(
        UserModel(
            id="legacy-sub",
            account_id=tenant.id,
            email="legacy@platform.example.com",
            password_hash="x",
            role_id=role_id,
            is_active=True,
            auth_provider="platform",
            external_id="legacy-sub",
        )
    )
    await db_session.commit()

    private_key, _ = platform_keys
    token = _platform_token(
        private_key, sub="legacy-sub", role="admin", email="legacy@platform.example.com"
    )
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    row = (
        await db_session.execute(select(UserModel).where(UserModel.id == "legacy-sub"))
    ).scalar_one()
    await db_session.refresh(row)
    assert row.account_id == SYSTEM_ACCOUNT_ID


@pytest.mark.asyncio
async def test_platform_principal_adopts_bootstrap_superadmin(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """Provisioning creates the instance's bootstrap superadmin from the procuring user's
    email, so that person already exists in SY0000 under a locally-generated id. The
    platform token carries the control-plane id instead, so inserting would violate
    UNIQUE(account_id, email). The existing operator row must be adopted, unmodified, so
    break-glass password login keeps working."""
    role_id = (
        await db_session.execute(select(RoleModel.id).where(RoleModel.name == "admin"))
    ).scalar_one()
    db_session.add(
        UserModel(
            id="bootstrap-generated-id",
            account_id=SYSTEM_ACCOUNT_ID,
            email="operator@example.com",
            password_hash="bootstrap-hash",
            role_id=role_id,
            is_active=True,
            auth_provider="password",
        )
    )
    await db_session.commit()

    private_key, _ = platform_keys
    token = _platform_token(
        private_key,
        sub="control-plane-user-id",
        role="admin",
        email="operator@example.com",
    )
    response = await client.get(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK, response.text

    rows = (
        await db_session.execute(
            select(UserModel).where(UserModel.email == "operator@example.com")
        )
    ).scalars().all()
    assert len(rows) == 1, "must adopt the bootstrap superadmin, not insert a duplicate"
    assert rows[0].id == "bootstrap-generated-id"
    assert rows[0].auth_provider == "password", "break-glass login must keep working"


@pytest.mark.asyncio
async def test_platform_sub_never_adopts_a_local_user(
    client, db_session, system_account, platform_keys, jwks_mock
):
    """`sub` is an id minted by another system. Without the auth_provider predicate a
    colliding id would authenticate the caller as that local user — and the migration
    above would then move an unrelated local user into SY0000."""
    tenant = AccountModel(
        id="00000000-0000-0000-0000-00000000cc03",
        account_code="CC0003",
        name="Tenant",
        slug="tenant-co",
    )
    db_session.add(tenant)
    await db_session.commit()

    role_id = (
        await db_session.execute(select(RoleModel.id).where(RoleModel.name == "admin"))
    ).scalar_one()
    db_session.add(
        UserModel(
            id="collide",
            account_id=tenant.id,
            email="local@tenant.example.com",
            password_hash="x",
            role_id=role_id,
            is_active=True,
            auth_provider="password",
            external_id=None,
        )
    )
    await db_session.commit()

    private_key, _ = platform_keys
    token = _platform_token(
        private_key, sub="collide", role="admin", email="operator@platform.example.com"
    )
    await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    local = (
        await db_session.execute(
            select(UserModel).where(
                UserModel.id == "collide", UserModel.auth_provider == "password"
            )
        )
    ).scalar_one()
    await db_session.refresh(local)
    assert local.account_id == tenant.id, "a local user must never be adopted or moved"
    assert local.email == "local@tenant.example.com"


@pytest.mark.asyncio
async def test_realtime_authenticate_accepts_platform_token(
    db_session, system_account, platform_keys, jwks_mock
):
    from snackbase.infrastructure.auth.token_types import TokenType
    from snackbase.infrastructure.realtime.realtime_auth import authenticate_realtime

    private_key, _ = platform_keys
    token = _platform_token(private_key, sub="rt-user", role="admin", email="rt@example.com")

    user = await authenticate_realtime(token, session=db_session)
    assert user.token_type == TokenType.PLATFORM
    assert user.email == "rt@example.com"
    assert user.account_id == SYSTEM_ACCOUNT_ID


@pytest.mark.asyncio
async def test_expired_platform_token_rejected_at_realtime_connect(
    db_session, system_account, platform_keys, jwks_mock
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
