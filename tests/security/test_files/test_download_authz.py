"""FILE-AUTHZ-*: file download authorization (M-04).

``download_file`` checks one thing: that the requested path begins with the
caller's ``account_id``. Nothing ties the file back to the record that
references it, so the collection rules that govern the record do not govern its
attachment.

Inside an account, that makes a file path a bearer token. Paths are UUIDs, so
guessing one is impractical — but paths are *not* secret: they are returned in
record payloads, echoed in webhooks, and stored in exports. Any user who has
ever seen a path keeps read access to that file even after losing read access
to the record.
"""

from __future__ import annotations

import json
import shutil
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.persistence.models import RoleModel, UserModel
from tests.security.helpers import assert_denied

OWNER_FILE_MARKER = "OWNER-ONLY-ATTACHMENT"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def restricted_attachment(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
    security_test_data: dict[str, Any],
) -> Any:
    """A record in Account A that only its creator may read, plus its file.

    Yields ``owner_token``, ``peer_token``, ``file_path``, ``record_id``.
    """
    account_a = security_test_data["account_a"]
    owner_token = security_test_data["user_a_token"]

    # A second user in the same account — same tenant, no access to the record.
    user_role = (
        await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    ).scalar_one()
    peer = UserModel(
        id=str(uuid.uuid4()),
        email=f"peer_{uuid.uuid4().hex[:6]}@example.com",
        account_id=account_a.id,
        password_hash="hashed_secret",
        role_id=user_role.id,
        is_active=True,
    )
    db_session.add(peer)
    await db_session.commit()
    peer_token = jwt_service.create_access_token(
        user_id=peer.id,
        account_id=peer.account_id,
        email=peer.email,
        role="user",
    )

    collection = f"docs_{uuid.uuid4().hex[:8]}"
    admin_headers = _auth(superadmin_token)

    created = await client.post(
        "/api/v1/collections",
        json={
            "name": collection,
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "attachment", "type": "file", "required": False},
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text

    # Only the creator may list or view the record.
    rules = await client.put(
        f"/api/v1/collections/{collection}/rules",
        json={
            "list_rule": "created_by = @request.auth.id",
            "view_rule": "created_by = @request.auth.id",
            "create_rule": "",
        },
        headers=admin_headers,
    )
    assert rules.status_code == 200, rules.text

    upload = await client.post(
        "/api/v1/files/upload",
        files={"file": ("private.txt", BytesIO(OWNER_FILE_MARKER.encode()), "text/plain")},
        headers=_auth(owner_token),
    )
    assert upload.status_code == 201, upload.text
    file_metadata = upload.json()["file"]
    file_path = file_metadata["path"]

    record = await client.post(
        f"/api/v1/records/{collection}",
        json={"title": "Owner only", "attachment": json.dumps(file_metadata)},
        headers=_auth(owner_token),
    )
    assert record.status_code == 201, record.text

    yield {
        "collection": collection,
        "owner_token": owner_token,
        "peer_token": peer_token,
        "file_path": file_path,
        "record_id": record.json()["id"],
    }

    shutil.rmtree(
        Path(get_settings().storage_path).resolve() / account_a.id, ignore_errors=True
    )


@pytest.mark.asyncio
async def test_file_authz_001_peer_cannot_read_the_owning_record(
    client: AsyncClient, restricted_attachment: dict[str, Any]
) -> None:
    """FILE-AUTHZ-001: precondition — the view rule really does exclude the peer."""
    response = await client.get(
        f"/api/v1/records/{restricted_attachment['collection']}"
        f"/{restricted_attachment['record_id']}",
        headers=_auth(restricted_attachment["peer_token"]),
    )

    assert_denied(response, allowed=(403, 404))


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-04 fix pending", strict=True)
async def test_file_authz_002_peer_denied_record_cannot_download_its_file(
    client: AsyncClient, restricted_attachment: dict[str, Any]
) -> None:
    """FILE-AUTHZ-002: losing read on the record must lose read on its file."""
    response = await client.get(
        f"/api/v1/files/{restricted_attachment['file_path']}",
        headers=_auth(restricted_attachment["peer_token"]),
    )

    assert_denied(response, allowed=(403, 404), leak_markers=(OWNER_FILE_MARKER,))


@pytest.mark.asyncio
async def test_file_authz_003_owner_can_download_its_file(
    client: AsyncClient, restricted_attachment: dict[str, Any]
) -> None:
    """FILE-AUTHZ-003: positive control — the record's owner still downloads it."""
    response = await client.get(
        f"/api/v1/files/{restricted_attachment['file_path']}",
        headers=_auth(restricted_attachment["owner_token"]),
    )

    assert response.status_code == 200, response.text
    assert OWNER_FILE_MARKER in response.text


@pytest.mark.asyncio
async def test_file_authz_004_cross_account_download_still_denied(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    restricted_attachment: dict[str, Any],
) -> None:
    """FILE-AUTHZ-004: regression — the account boundary still holds."""
    response = await client.get(
        f"/api/v1/files/{restricted_attachment['file_path']}",
        headers=_auth(security_test_data["user_b_token"]),
    )

    assert_denied(response, leak_markers=(OWNER_FILE_MARKER,))
