"""Integration tests for Codelist REST API (Phase 2)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.codelist_service import CodelistService
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.role import RoleModel
from snackbase.infrastructure.persistence.models.user import UserModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ACCOUNT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def _make_user(
    db_session: AsyncSession,
    *,
    user_id: str,
    email: str,
    account_id: str,
    role_name: str = "admin",
) -> str:
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == role_name))
    ).scalar_one()
    if await db_session.get(AccountModel, account_id) is None:
        code = account_id[:2].upper() + "0001"
        db_session.add(
            AccountModel(
                id=account_id,
                account_code=code if len(code) == 6 else "AA0001",
                slug=f"slug-{user_id}"[:32],
                name=f"Account {user_id}",
            )
        )
        await db_session.flush()
    user = UserModel(
        id=user_id,
        email=email,
        account_id=account_id,
        password_hash="hashed",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user_id,
        account_id=account_id,
        email=email,
        role=role_name,
    )


@pytest.fixture
async def admin_a_token(db_session: AsyncSession) -> str:
    # Ensure unique account codes
    if await db_session.get(AccountModel, ACCOUNT_A) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_A,
                account_code="AA1111",
                slug="account-a-api",
                name="Account A",
            )
        )
        await db_session.commit()
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    ).scalar_one()
    user = UserModel(
        id="admin_a",
        email="admin_a@test.com",
        account_id=ACCOUNT_A,
        password_hash="hashed",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id="admin_a",
        account_id=ACCOUNT_A,
        email="admin_a@test.com",
        role="admin",
    )


@pytest.fixture
async def admin_b_token(db_session: AsyncSession) -> str:
    if await db_session.get(AccountModel, ACCOUNT_B) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_B,
                account_code="BB2222",
                slug="account-b-api",
                name="Account B",
            )
        )
        await db_session.commit()
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    ).scalar_one()
    user = UserModel(
        id="admin_b",
        email="admin_b@test.com",
        account_id=ACCOUNT_B,
        password_hash="hashed",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id="admin_b",
        account_id=ACCOUNT_B,
        email="admin_b@test.com",
        role="admin",
    )


@pytest.fixture
async def user_a_token(db_session: AsyncSession) -> str:
    if await db_session.get(AccountModel, ACCOUNT_A) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_A,
                account_code="AA1111",
                slug="account-a-api",
                name="Account A",
            )
        )
        await db_session.commit()
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    user = UserModel(
        id="user_a",
        email="user_a@test.com",
        account_id=ACCOUNT_A,
        password_hash="hashed",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return jwt_service.create_access_token(
        user_id="user_a",
        account_id=ACCOUNT_A,
        email="user_a@test.com",
        role="user",
    )


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient):
    r = await client.get("/api/v1/codelists")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_effective_values_for_operator_created_list(
    client: AsyncClient, superadmin_token: str, admin_a_token: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "priority", "name": "Priority", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/priority/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "p1",
            "labels": [{"language": "en", "label": "Priority One"}],
        },
    )
    r = await client.get(
        "/api/v1/codelists/priority/values?lang=en",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    assert r.status_code == 200, r.text
    codes = {v["code"] for v in r.json()}
    assert "p1" in codes
    p1 = next(v for v in r.json() if v["code"] == "p1")
    assert p1["label"] == "Priority One"


@pytest.mark.asyncio
async def test_superadmin_manages_system_values_and_labels(
    client: AsyncClient, superadmin_token: str
):
    # Create system codelist
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "countries",
            "name": "Countries",
            "scope": "system",
            "is_extensible": False,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_system"] is True

    # Add value with labels
    r = await client.post(
        "/api/v1/codelists/countries/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "de",
            "sort_order": 1,
            "labels": [
                {"language": "en", "label": "Germany"},
                {"language": "ja", "label": "ドイツ"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["code"] == "de"

    r = await client.get(
        "/api/v1/codelists/countries/values?lang=ja",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert r.status_code == 200
    assert any(v["label"] == "ドイツ" for v in r.json())


@pytest.mark.asyncio
async def test_account_admin_cannot_create_system(
    client: AsyncClient, admin_a_token: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"code": "hack", "name": "Hack", "scope": "system"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_account_private_list_and_isolation(
    client: AsyncClient, admin_a_token: str, admin_b_token: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"code": "private_a", "name": "Private A", "scope": "account"},
    )
    assert r.status_code == 201, r.text

    r = await client.post(
        "/api/v1/codelists/private_a/manage/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"code": "x1", "labels": [{"language": "en", "label": "X One"}]},
    )
    assert r.status_code == 201, r.text

    # A sees effective
    r = await client.get(
        "/api/v1/codelists/private_a/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    assert r.status_code == 200
    assert any(v["code"] == "x1" for v in r.json())

    # B cannot get private list
    r = await client.get(
        "/api/v1/codelists/private_a",
        headers={"Authorization": f"Bearer {admin_b_token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_non_extensible_rejects_extension(
    client: AsyncClient, superadmin_token: str, admin_a_token: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "locked_list",
            "name": "Locked",
            "scope": "system",
            "is_extensible": False,
        },
    )
    r = await client.post(
        "/api/v1/codelists/locked_list/manage/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"code": "x99"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_extensible_allows_account_extension(
    client: AsyncClient, superadmin_token: str, admin_a_token: str, admin_b_token: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "tags",
            "name": "Tags",
            "scope": "system",
            "is_extensible": True,
        },
    )
    assert r.status_code == 201, r.text
    await client.post(
        "/api/v1/codelists/tags/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "base", "labels": [{"language": "en", "label": "Base"}]},
    )
    r = await client.post(
        "/api/v1/codelists/tags/manage/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"code": "only_a", "labels": [{"language": "en", "label": "Only A"}]},
    )
    assert r.status_code == 201, r.text

    ra = await client.get(
        "/api/v1/codelists/tags/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    rb = await client.get(
        "/api/v1/codelists/tags/values",
        headers={"Authorization": f"Bearer {admin_b_token}"},
    )
    assert "only_a" in {v["code"] for v in ra.json()}
    assert "only_a" not in {v["code"] for v in rb.json()}
    assert "base" in {v["code"] for v in rb.json()}


@pytest.mark.asyncio
async def test_override_hide_isolation(
    client: AsyncClient,
    superadmin_token: str,
    admin_a_token: str,
    admin_b_token: str,
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "opts", "name": "Opts", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/opts/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "hide_me", "labels": [{"language": "en", "label": "Hide Me"}]},
    )
    await client.post(
        "/api/v1/codelists/opts/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "keep", "labels": [{"language": "en", "label": "Keep"}]},
    )

    r = await client.put(
        "/api/v1/codelists/opts/values/hide_me/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"visibility": "hidden"},
    )
    assert r.status_code == 200, r.text

    ra = await client.get(
        "/api/v1/codelists/opts/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    rb = await client.get(
        "/api/v1/codelists/opts/values",
        headers={"Authorization": f"Bearer {admin_b_token}"},
    )
    assert "hide_me" not in {v["code"] for v in ra.json()}
    assert "hide_me" in {v["code"] for v in rb.json()}

    # Clear restore
    r = await client.delete(
        "/api/v1/codelists/opts/values/hide_me/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    assert r.status_code == 200
    ra2 = await client.get(
        "/api/v1/codelists/opts/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    assert "hide_me" in {v["code"] for v in ra2.json()}


@pytest.mark.asyncio
async def test_override_invalid_value_404(
    client: AsyncClient, superadmin_token: str, admin_a_token: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "ov404", "name": "OV404", "scope": "system"},
    )
    r = await client.put(
        "/api/v1/codelists/ov404/values/no-such/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"visibility": "hidden"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_default_flips_previous(
    client: AsyncClient, superadmin_token: str, admin_a_token: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "defs_api", "name": "Defs", "scope": "system"},
    )
    for c in ("d1", "d2"):
        await client.post(
            "/api/v1/codelists/defs_api/manage/values",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"code": c},
        )
    await client.put(
        "/api/v1/codelists/defs_api/values/d1/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"is_default": True},
    )
    await client.put(
        "/api/v1/codelists/defs_api/values/d2/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"is_default": True},
    )
    r = await client.get(
        "/api/v1/codelists/defs_api/values",
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    defaults = [v for v in r.json() if v["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["code"] == "d2"


@pytest.mark.asyncio
async def test_non_admin_cannot_mutate(
    client: AsyncClient, user_a_token: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {user_a_token}"},
        json={"code": "nope", "name": "Nope", "scope": "account"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_superadmin_preview_account_id(
    client: AsyncClient,
    superadmin_token: str,
    admin_a_token: str,
    db_session: AsyncSession,
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "preview_cl", "name": "Preview", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/preview_cl/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "v1"},
    )
    await client.put(
        "/api/v1/codelists/preview_cl/values/v1/override",
        headers={"Authorization": f"Bearer {admin_a_token}"},
        json={"visibility": "hidden"},
    )
    r = await client.get(
        f"/api/v1/codelists/preview_cl/values?account_id={ACCOUNT_A}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert r.status_code == 200
    assert "v1" not in {v["code"] for v in r.json()}


@pytest.mark.asyncio
async def test_system_list_with_values_hard_delete_rejected(
    client: AsyncClient, superadmin_token: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "sys_vals", "name": "Sys", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/sys_vals/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "v"},
    )
    r = await client.delete(
        "/api/v1/codelists/sys_vals?hard=true",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    # Non-empty system list cannot hard-delete
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_openapi_includes_codelist_paths(client: AsyncClient):
    # openapi may be disabled in some envs; check route registration via app
    from snackbase.infrastructure.api.app import app

    # FastAPI keeps `include_router` results behind opaque router objects
    # instead of flattening them into `app.routes`, so assert on the generated
    # schema — the same registration, expressed as the public contract.
    assert any("/codelists" in p for p in app.openapi()["paths"])
    # If openapi available
    r = await client.get("/openapi.json")
    if r.status_code == 200:
        spec_paths = r.json().get("paths", {})
        assert any("codelists" in p for p in spec_paths)


@pytest.mark.asyncio
async def test_assert_in_codelist_via_service(db_session: AsyncSession):
    """Validator helper unit path driven through service on migrated DB."""
    from snackbase.infrastructure.persistence.repositories.codelist_repository import (
        SYSTEM_ACCOUNT_ID,
    )

    svc = CodelistService(db_session)
    if await db_session.get(AccountModel, ACCOUNT_A) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_A,
                account_code="AA1111",
                slug="account-a-api2",
                name="Account A",
            )
        )
        await db_session.commit()
    await svc.create_codelist(
        code="assert_cl",
        name="Assert",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await svc.add_value(
        "assert_cl", code="ok", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    ok = await svc.assert_in_codelist(ACCOUNT_A, "assert_cl", "ok")
    assert ok.code == "ok"
    with pytest.raises(Exception):
        await svc.assert_in_codelist(ACCOUNT_A, "assert_cl", "nope")
