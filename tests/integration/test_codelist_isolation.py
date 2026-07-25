"""Security isolation suite for codelist APIs (Phase 5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.role import RoleModel
from snackbase.infrastructure.persistence.models.user import UserModel

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ACCOUNT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def _admin_token(
    db_session: AsyncSession,
    *,
    user_id: str,
    email: str,
    account_id: str,
    account_code: str,
    slug: str,
) -> str:
    if await db_session.get(AccountModel, account_id) is None:
        db_session.add(
            AccountModel(
                id=account_id,
                account_code=account_code,
                slug=slug,
                name=f"Account {slug}",
            )
        )
        await db_session.commit()
    role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    ).scalar_one()
    if await db_session.get(UserModel, user_id) is None:
        db_session.add(
            UserModel(
                id=user_id,
                email=email,
                account_id=account_id,
                password_hash="hashed",
                role=role,
                is_active=True,
            )
        )
        await db_session.commit()
    return jwt_service.create_access_token(
        user_id=user_id,
        account_id=account_id,
        email=email,
        role="admin",
    )


@pytest.fixture
async def token_a(db_session: AsyncSession) -> str:
    return await _admin_token(
        db_session,
        user_id="iso_admin_a",
        email="iso_a@test.com",
        account_id=ACCOUNT_A,
        account_code="AA3333",
        slug="iso-a",
    )


@pytest.fixture
async def token_b(db_session: AsyncSession) -> str:
    return await _admin_token(
        db_session,
        user_id="iso_admin_b",
        email="iso_b@test.com",
        account_id=ACCOUNT_B,
        account_code="BB3333",
        slug="iso-b",
    )


@pytest.mark.asyncio
async def test_private_list_not_visible_cross_account(
    client: AsyncClient, token_a: str, token_b: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"code": "secret_iso", "name": "Secret", "scope": "account"},
    )
    assert r.status_code == 201, r.text
    await client.post(
        "/api/v1/codelists/secret_iso/manage/values",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"code": "x", "labels": [{"language": "en", "label": "X"}]},
    )
    # B cannot get metadata
    r = await client.get(
        "/api/v1/codelists/secret_iso",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
    # B list does not include secret
    r = await client.get(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert "secret_iso" not in {c["code"] for c in r.json()}


@pytest.mark.asyncio
async def test_extension_isolation(
    client: AsyncClient, superadmin_token: str, token_a: str, token_b: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "iso_ext",
            "name": "Ext",
            "scope": "system",
            "is_extensible": True,
        },
    )
    await client.post(
        "/api/v1/codelists/iso_ext/manage/values",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"code": "only_a"},
    )
    ra = await client.get(
        "/api/v1/codelists/iso_ext/values",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    rb = await client.get(
        "/api/v1/codelists/iso_ext/values",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert "only_a" in {v["code"] for v in ra.json()}
    assert "only_a" not in {v["code"] for v in rb.json()}


@pytest.mark.asyncio
async def test_override_isolation(
    client: AsyncClient, superadmin_token: str, token_a: str, token_b: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "iso_ov", "name": "OV", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/iso_ov/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "shared"},
    )
    await client.put(
        "/api/v1/codelists/iso_ov/values/shared/override",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"visibility": "hidden"},
    )
    ra = await client.get(
        "/api/v1/codelists/iso_ov/values",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    rb = await client.get(
        "/api/v1/codelists/iso_ov/values",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert "shared" not in {v["code"] for v in ra.json()}
    assert "shared" in {v["code"] for v in rb.json()}


@pytest.mark.asyncio
async def test_account_admin_cannot_create_system(
    client: AsyncClient, token_a: str
):
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"code": "evil_sys", "name": "Evil", "scope": "system"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_account_id_injection_on_effective_values_denied(
    client: AsyncClient, token_a: str
):
    """Non-superadmin cannot pass account_id to preview another tenant."""
    r = await client.get(
        f"/api/v1/codelists/regions/values?account_id={ACCOUNT_B}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_account_id_injection_on_override_denied(
    client: AsyncClient, superadmin_token: str, token_a: str
):
    await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "iso_inj", "name": "Inj", "scope": "system"},
    )
    await client.post(
        "/api/v1/codelists/iso_inj/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "v1"},
    )
    r = await client.put(
        f"/api/v1/codelists/iso_inj/values/v1/override?account_id={ACCOUNT_B}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"visibility": "hidden"},
    )
    assert r.status_code == 403
