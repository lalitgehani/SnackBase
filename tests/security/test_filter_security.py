"""Security tests for the advanced filtering feature.

Tests cover:
- SQL injection via filter values (must be parameterized)
- Tenant isolation: filter cannot access other accounts' records
- Context variable rejection at the API layer
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from snackbase.infrastructure.auth.jwt_service import jwt_service

COLLECTION = "sec_filter_col"
SCHEMA = [
    {"name": "title", "type": "text", "required": True},
    {"name": "secret", "type": "text"},
    {"name": "status", "type": "text"},
]


@pytest.fixture(autouse=True)
async def setup_multi_tenant_collection(
    client: AsyncClient, superadmin_token, regular_user_token, db_session: AsyncSession
):
    """Set up a collection and two separate accounts' records."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create collection with open rules
    await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "label": "Security Filter Test", "schema": SCHEMA},
        headers=headers,
    )
    await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )

    # Create a record in user account
    user_headers = {"Authorization": f"Bearer {regular_user_token}"}
    await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "User Record", "status": "active", "secret": "user_secret"},
        headers=user_headers,
    )

    # Create a record as superadmin (different account)
    await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={
            "title": "Admin Record",
            "status": "active",
            "secret": "admin_secret",
        },
        headers=headers,
    )

    yield

    await client.delete(f"/api/v1/collections/{COLLECTION}", headers=headers)


@pytest.mark.asyncio
async def test_sql_injection_via_filter_value_is_safe(
    client: AsyncClient, superadmin_token
):
    """SQL injection attempt in filter value must be parameterized and not executed."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Try to inject SQL via string value
    malicious_filter = "title = \"'; DROP TABLE sec_filter_col; --\""
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": malicious_filter},
        headers=headers,
    )
    # Should return 200 with empty results (not a 500 or a dropped table)
    assert resp.status_code == 200
    # Collection should still be accessible (not dropped)
    check = await client.get(f"/api/v1/records/{COLLECTION}", headers=headers)
    assert check.status_code == 200


@pytest.mark.asyncio
async def test_sql_injection_via_filter_value_in_operator(
    client: AsyncClient, superadmin_token
):
    """SQL injection attempt via IN operator values must be safe."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    malicious_filter = "title IN (\"'; DROP TABLE sec_filter_col; --\", 'ok')"
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": malicious_filter},
        headers=headers,
    )
    assert resp.status_code == 200
    # Table should still exist
    check = await client.get(f"/api/v1/records/{COLLECTION}", headers=headers)
    assert check.status_code == 200


@pytest.mark.asyncio
async def test_tenant_isolation_with_filter(
    client: AsyncClient, regular_user_token
):
    """A user with a filter can only see their own account's records."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status = "active"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Should only see records from their own account (1 record, not 2)
    assert data["total"] == 1
    assert data["items"][0]["title"] == "User Record"


@pytest.mark.asyncio
async def test_filter_account_id_cannot_bypass_tenant_isolation(
    client: AsyncClient, regular_user_token, superadmin_token, db_session: AsyncSession
):
    """Filtering on account_id for another account still returns no results."""
    # Get superadmin's account_id
    from snackbase.infrastructure.persistence.models.user import UserModel

    res = await db_session.execute(
        select(UserModel).where(UserModel.id == "superadmin")
    )
    superadmin_user = res.scalar_one_or_none()
    if superadmin_user is None:
        pytest.skip("Superadmin user not found")

    superadmin_account_id = superadmin_user.account_id

    # Try to filter for superadmin's account records using regular user token
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": f'account_id = "{superadmin_account_id}"'},
        headers=headers,
    )
    assert resp.status_code == 200
    # The account_id WHERE clause always scopes to the user's own account,
    # so even if they filter for another account_id, they get 0 results
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_context_variable_in_filter_returns_400(
    client: AsyncClient, regular_user_token
):
    """Context variables in filters must be rejected with 400."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": '@request.auth.id = "anything"'},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_filter_cannot_read_other_tenants_secrets(
    client: AsyncClient, regular_user_token
):
    """A filter on a field value does not leak other tenants' data."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'secret = "admin_secret"'},
        headers=headers,
    )
    assert resp.status_code == 200
    # Even if they guess the admin secret, tenant isolation returns 0 results
    assert resp.json()["total"] == 0
