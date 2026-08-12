"""AUTH-INV-*: invitation-token storage (M-06).

``create_invitation`` generates a 64-hex token and writes it into
``invitations.token`` verbatim. The value is also mailed to the invitee and
returned in the API response, so the database column holds a live credential.

The same codebase already does this correctly elsewhere: password-reset tokens
are hashed at rest and compared by hash. An invitation grants account
membership, so read access to the table — a backup, a replica, a SQL-injection
read, an over-broad support query — is enough to join any pending invitation's
account before its 48-hour window closes.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.invitation import InvitationModel


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_invitation(
    client: AsyncClient, token: str, email: str
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/invitations",
        json={"email": email, "role": "user"},
        headers=_auth(token),
    )
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


async def _stored_token(db_session: AsyncSession, invitation_id: str) -> str:
    row = (
        await db_session.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
    ).scalar_one()
    await db_session.refresh(row)
    return str(row.token)


@pytest.mark.asyncio
async def test_auth_inv_001_stored_token_is_not_the_plaintext(
    client: AsyncClient,
    db_session: AsyncSession,
    security_test_data: dict[str, Any],
) -> None:
    """AUTH-INV-001: the DB column must hold a hash, not the issued token."""
    invitation = await _create_invitation(
        client, security_test_data["user_a_token"], "invitee-hash@example.com"
    )

    stored = await _stored_token(db_session, invitation["id"])

    assert stored != invitation["token"], (
        "the invitation token is stored in plaintext — DB read access yields "
        "live account-membership credentials"
    )


@pytest.mark.asyncio
async def test_auth_inv_002_acceptance_works_with_the_issued_token(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """AUTH-INV-002: the issued token still resolves an invitation.

    Kept independent of the storage format so it stays valid once hashing lands
    — a hashed column must still be looked up by hashing the presented value.
    """
    invitation = await _create_invitation(
        client, security_test_data["user_a_token"], "invitee-accept@example.com"
    )

    response = await client.get(f"/api/v1/invitations/{invitation['token']}")

    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_auth_inv_003_guessed_token_is_rejected(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """AUTH-INV-003: an invalid token resolves nothing."""
    await _create_invitation(
        client, security_test_data["user_a_token"], "invitee-guess@example.com"
    )

    response = await client.get("/api/v1/invitations/" + "0" * 64)

    assert response.status_code == 404
