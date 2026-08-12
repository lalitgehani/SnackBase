"""Integration tests for Anonymous / Public Access.

Verifies that collection rules with empty string ("") allow unauthenticated access,
while locked (None) rules return 403 and expression rules return 401 for anonymous.
"""

import pytest
from httpx import AsyncClient


COLLECTION = "anon_test_col"
SCHEMA = [
    {"name": "title", "type": "text", "required": True},
    {"name": "status", "type": "text"},
]

# The regular_user_token fixture creates an account with slug="reg-user-acc"
ACCOUNT_SLUG = "reg-user-acc"


@pytest.fixture(autouse=True)
async def setup_collection(client: AsyncClient, superadmin_token, regular_user_token):
    """Create collection and seed a record before each test."""
    sa_headers = {"Authorization": f"Bearer {superadmin_token}"}
    user_headers = {"Authorization": f"Bearer {regular_user_token}"}

    # Create collection (superadmin)
    resp = await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "label": "Anon Test", "schema": SCHEMA},
        headers=sa_headers,
    )
    assert resp.status_code == 201, f"Failed to create collection: {resp.text}"

    # Open create rule so we can seed a record; individual tests will override rules as needed
    resp = await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=sa_headers,
    )
    assert resp.status_code == 200, f"Failed to open rules for seeding: {resp.text}"

    # Seed a record as the regular user so it belongs to reg-user-acc
    resp = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "Hello World", "status": "published"},
        headers=user_headers,
    )
    assert resp.status_code == 201, f"Failed to seed record: {resp.text}"
    # Store seeded record id for later use within tests
    pytest._anon_record_id = resp.json()["id"]

    yield

    # Cleanup
    await client.delete(f"/api/v1/collections/{COLLECTION}", headers=sa_headers)


async def _set_rules(client, superadmin_token, **kwargs):
    """Helper to PUT collection rules."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    default = {
        "list_rule": None,
        "view_rule": None,
        "create_rule": None,
        "update_rule": None,
        "delete_rule": None,
    }
    default.update(kwargs)
    resp = await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        json=default,
        headers=headers,
    )
    assert resp.status_code == 200, f"Failed to set rules: {resp.text}"


# ---------------------------------------------------------------------------
# Anonymous LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_list_public_collection(client: AsyncClient, superadmin_token):
    """Anonymous user can list records when list_rule is ''."""
    await _set_rules(client, superadmin_token, list_rule="")

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(r["account_id"] for r in data["items"])


@pytest.mark.asyncio
async def test_anonymous_list_locked_collection(client: AsyncClient, superadmin_token):
    """Anonymous user gets 403 when list_rule is None (locked)."""
    await _set_rules(client, superadmin_token, list_rule=None)

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_list_expression_rule_returns_401(client: AsyncClient, superadmin_token):
    """Anonymous user gets 401 when list_rule requires auth context (expression)."""
    await _set_rules(client, superadmin_token, list_rule='created_by = @request.auth.id')

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Anonymous GET
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_get_public_collection(client: AsyncClient, superadmin_token):
    """Anonymous user can fetch a single record when view_rule is ''."""
    await _set_rules(client, superadmin_token, list_rule="", view_rule="")
    record_id = pytest._anon_record_id

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == record_id


@pytest.mark.asyncio
async def test_anonymous_get_locked_collection(client: AsyncClient, superadmin_token):
    """Anonymous user gets 403 on locked view_rule."""
    await _set_rules(client, superadmin_token, view_rule=None)
    record_id = pytest._anon_record_id

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Anonymous CREATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_create_public_collection(client: AsyncClient, superadmin_token):
    """Anonymous user can create a record when create_rule is '' and created_by is null."""
    await _set_rules(client, superadmin_token, create_rule="")

    resp = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "Anonymous Record", "status": "draft"},
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Anonymous Record"
    assert data["created_by"] == "anonymous"
    assert data["updated_by"] == "anonymous"


@pytest.mark.asyncio
async def test_anonymous_create_locked_collection(client: AsyncClient, superadmin_token):
    """Anonymous user gets 403 when create_rule is None."""
    await _set_rules(client, superadmin_token, create_rule=None)

    resp = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "Should Fail"},
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Anonymous UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_update_public_collection(client: AsyncClient, superadmin_token):
    """Anonymous user can update a record when update_rule is '' and updated_by is null."""
    await _set_rules(
        client, superadmin_token,
        list_rule="", view_rule="", update_rule=""
    )
    record_id = pytest._anon_record_id

    resp = await client.patch(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        json={"status": "updated_by_anon"},
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "updated_by_anon"
    assert data["updated_by"] == "anonymous"


@pytest.mark.asyncio
async def test_anonymous_update_locked_collection(client: AsyncClient, superadmin_token):
    """Anonymous user gets 403 when update_rule is None."""
    await _set_rules(client, superadmin_token, view_rule="", update_rule=None)
    record_id = pytest._anon_record_id

    resp = await client.patch(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        json={"status": "should_fail"},
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Anonymous DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_delete_public_collection(client: AsyncClient, superadmin_token, regular_user_token):
    """Anonymous user can delete a record when delete_rule is ''."""
    await _set_rules(
        client, superadmin_token,
        create_rule="", delete_rule=""
    )

    # Create a fresh record as anonymous so we can delete it
    create_resp = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "To Delete", "status": "draft"},
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert create_resp.status_code == 201
    new_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/records/{COLLECTION}/{new_id}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_anonymous_delete_locked_collection(client: AsyncClient, superadmin_token):
    """Anonymous user gets 403 when delete_rule is None."""
    await _set_rules(client, superadmin_token, view_rule="", delete_rule=None)
    record_id = pytest._anon_record_id

    resp = await client.delete(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        headers={"X-Account-ID": ACCOUNT_SLUG},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# X-Account-ID header validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_account_id_header_returns_400(client: AsyncClient, superadmin_token):
    """Anonymous request without X-Account-ID header returns 400."""
    await _set_rules(client, superadmin_token, list_rule="")

    resp = await client.get(f"/api/v1/records/{COLLECTION}")
    assert resp.status_code == 400
    assert "X-Account-ID" in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_invalid_account_id_header_returns_404(client: AsyncClient, superadmin_token):
    """Anonymous request with non-existent account in X-Account-ID returns 404."""
    await _set_rules(client, superadmin_token, list_rule="")

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"X-Account-ID": "nonexistent-account-slug"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Authenticated user on public collection (regression guard)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_user_on_public_collection(client: AsyncClient, superadmin_token, regular_user_token):
    """Authenticated user can access a public collection normally."""
    await _set_rules(client, superadmin_token, list_rule="")

    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_jwt_takes_precedence_over_x_account_id(
    client: AsyncClient, superadmin_token, regular_user_token
):
    """When JWT is present, X-Account-ID header is ignored (JWT account wins)."""
    await _set_rules(client, superadmin_token, list_rule="")

    # Send a wrong account slug in the header; JWT account should still resolve
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={
            "Authorization": f"Bearer {regular_user_token}",
            "X-Account-ID": "nonexistent-account-slug",
        },
    )
    # The request should succeed because JWT is present — X-Account-ID is ignored server-side
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Account isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_cannot_see_other_accounts_records(
    client: AsyncClient, superadmin_token, regular_user_token
):
    """Anonymous requests are scoped to the specified account; other accounts' records invisible."""
    await _set_rules(client, superadmin_token, list_rule="", create_rule="")

    # Create a record belonging to the regular user's account
    user_headers = {"Authorization": f"Bearer {regular_user_token}"}
    r = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"title": "User Account Record"},
        headers=user_headers,
    )
    assert r.status_code == 201
    user_record_id = r.json()["id"]
    user_account_id = r.json()["account_id"]

    # Create a second account and use its slug in X-Account-ID
    sa_headers = {"Authorization": f"Bearer {superadmin_token}"}
    second_account_resp = await client.post(
        "/api/v1/accounts",
        json={"name": "Second Account", "slug": "second-account-anon-test"},
        headers=sa_headers,
    )
    assert second_account_resp.status_code == 201

    # Anonymous request scoped to second account should not see first account's records
    anon_resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        headers={"X-Account-ID": "second-account-anon-test"},
    )
    assert anon_resp.status_code == 200
    returned_ids = [r["id"] for r in anon_resp.json()["items"]]
    assert user_record_id not in returned_ids

    # Cleanup second account
    second_account_id = second_account_resp.json()["id"]
    await client.delete(f"/api/v1/accounts/{second_account_id}", headers=sa_headers)
