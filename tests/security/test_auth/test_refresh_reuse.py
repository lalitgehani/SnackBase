"""AUTH-RF-*: refresh-token reuse detection (M-05).

Rotation works: `/auth/refresh` revokes the presented token and issues a new
pair, so replaying a rotated-out token is refused. What is missing is the
*response* to that replay.

Presenting an already-revoked token is not an ordinary error — a valid token
that has already been spent means two parties hold it, so one of them is an
attacker. The standard answer is family revocation: kill every refresh token
for that user so both the thief and the victim are forced to re-authenticate.
Today the replay is logged and the attacker's *other* token, or the victim's
live token, keeps working.

``RefreshTokenRepository.revoke_all_for_user`` already exists; nothing calls it
from the reuse path.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth import hash_password
from snackbase.infrastructure.persistence.models import AccountModel, RoleModel, UserModel


@pytest_asyncio.fixture
async def refresh_user(db_session: AsyncSession) -> dict[str, Any]:
    """A password-auth user who can obtain real refresh tokens."""
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()

    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="RF0001",
        name="Refresh Test Account",
        slug=f"refresh-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(account)

    password = "RotateMe123!"
    user = UserModel(
        id=str(uuid.uuid4()),
        email=f"rf-{uuid.uuid4().hex[:6]}@example.com",
        account_id=account.id,
        password_hash=hash_password(password),
        role_id=user_role.id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    return {
        "email": user.email,
        "password": password,
        "account": account.account_code,
        "user_id": user.id,
        "account_id": account.id,
    }


async def _login(client: AsyncClient, user: dict[str, Any]) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user["email"],
            "password": user["password"],
            "account": user["account"],
        },
    )
    assert response.status_code == 200, response.text
    return str(response.json()["refresh_token"])


async def _refresh(client: AsyncClient, refresh_token: str) -> Any:
    return await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )


@pytest.mark.asyncio
async def test_auth_rf_001_normal_rotation_still_works(
    client: AsyncClient, refresh_user: dict[str, Any]
) -> None:
    """AUTH-RF-001: regression — an unused refresh token rotates successfully."""
    original = await _login(client, refresh_user)

    rotated = await _refresh(client, original)

    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != original


@pytest.mark.asyncio
async def test_auth_rf_002_rotated_out_token_is_refused(
    client: AsyncClient, refresh_user: dict[str, Any]
) -> None:
    """AUTH-RF-002: regression — replaying a spent token returns 401."""
    original = await _login(client, refresh_user)
    first = await _refresh(client, original)
    assert first.status_code == 200, first.text

    replay = await _refresh(client, original)

    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_auth_rf_003_reuse_revokes_the_whole_token_family(
    client: AsyncClient, refresh_user: dict[str, Any]
) -> None:
    """AUTH-RF-003: a replay must invalidate every refresh token for the user."""
    original = await _login(client, refresh_user)
    rotated = await _refresh(client, original)
    assert rotated.status_code == 200, rotated.text
    live_token = rotated.json()["refresh_token"]

    replay = await _refresh(client, original)
    assert replay.status_code == 401

    # The live token was issued before the theft was detected, so it is just as
    # compromised — it must not survive.
    after_detection = await _refresh(client, live_token)

    assert after_detection.status_code == 401, (
        "the previously-issued refresh token survived a detected reuse"
    )


@pytest.mark.asyncio
async def test_auth_rf_004_reuse_revokes_other_sessions(
    client: AsyncClient, refresh_user: dict[str, Any]
) -> None:
    """AUTH-RF-004: family revocation covers concurrently-issued sessions."""
    stolen = await _login(client, refresh_user)
    other_session = await _login(client, refresh_user)

    rotated = await _refresh(client, stolen)
    assert rotated.status_code == 200, rotated.text

    replay = await _refresh(client, stolen)
    assert replay.status_code == 401

    survivor = await _refresh(client, other_session)

    assert survivor.status_code == 401, (
        "an unrelated session survived a detected refresh-token reuse"
    )
