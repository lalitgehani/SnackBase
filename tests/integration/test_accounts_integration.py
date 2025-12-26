"""Integration tests for Accounts API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import AccountModel, UserModel


@pytest.mark.asyncio
async def test_account_crud_lifecycle(client: AsyncClient, superadmin_token: str):
    """Test full CRUD lifecycle of an account."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # 1. Create Account
    payload = {"name": "Integration Test Account", "slug": "int-test"}
    response = await client.post("/api/v1/accounts", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    account_id = data["id"]
    assert data["name"] == "Integration Test Account"
    assert data["slug"] == "int-test"

    # 2. Get Account
    response = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == account_id

    # 3. Update Account
    response = await client.put(
        f"/api/v1/accounts/{account_id}", 
        json={"name": "Updated Name"}, 
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

    # 4. List Accounts verify it appears
    response = await client.get("/api/v1/accounts?search=int-test", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["id"] == account_id for item in items)

    # 5. Delete Account
    response = await client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
    assert response.status_code == 204

    # 6. Verify Deletion
    response = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_account_list_pagination(client: AsyncClient, superadmin_token: str):
    """Verify pagination works correctly."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create enough accounts to span pages is slow in integration,
    # but we can rely on existing seed or create a few.
    # The DB is reset per session/function depending on fixture scope.
    # We'll create 5 accounts to test small pages.
    for i in range(5):
        await client.post(
            "/api/v1/accounts",
            json={"name": f"Page Account {i}", "slug": f"page-acc-{i}"},
            headers=headers
        )

    # Convert default page size via query params
    response = await client.get(
        "/api/v1/accounts?page=1&page_size=2", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5

    # Page 2
    response = await client.get(
        "/api/v1/accounts?page=2&page_size=2", headers=headers
    )
    assert response.status_code == 200
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_account_search_functionality(client: AsyncClient, superadmin_token: str):
    """Verify search by name, slug, ID."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create target
    response = await client.post(
        "/api/v1/accounts",
        json={"name": "Search Target", "slug": "find-me"},
        headers=headers
    )
    target_id = response.json()["id"]

    # Search Name
    resp = await client.get("/api/v1/accounts?search=Target", headers=headers)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["id"] == target_id

    # Search Slug
    resp = await client.get("/api/v1/accounts?search=find-me", headers=headers)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["slug"] == "find-me"

    # Search ID
    resp = await client.get(f"/api/v1/accounts?search={target_id}", headers=headers)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["id"] == target_id


@pytest.mark.asyncio
async def test_account_sort_functionality(client: AsyncClient, superadmin_token: str):
    """Verify sorting."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create A and Z accounts
    await client.post("/api/v1/accounts", json={"name": "A Account"}, headers=headers)
    await client.post("/api/v1/accounts", json={"name": "Z Account"}, headers=headers)

    # Sort ASC
    resp = await client.get(
        "/api/v1/accounts?sort_by=name&sort_order=asc", headers=headers
    )
    items = resp.json()["items"]
    names = [i["name"] for i in items if "Account" in i["name"]]
    # Should be sorted (A then Z) - might include other accounts from other tests if session shared
    # But names list should be sorted relative to each other if we filter
    
    # Check if 'A Account' comes before 'Z Account' index-wise
    a_idx = next(i for i, n in enumerate(names) if n == "A Account")
    z_idx = next(i for i, n in enumerate(names) if n == "Z Account")
    assert a_idx < z_idx

    # Sort DESC
    resp = await client.get(
        "/api/v1/accounts?sort_by=name&sort_order=desc", headers=headers
    )
    items = resp.json()["items"]
    names = [i["name"] for i in items if "Account" in i["name"]]
    a_idx = next(i for i, n in enumerate(names) if n == "A Account")
    z_idx = next(i for i, n in enumerate(names) if n == "Z Account")
    assert z_idx < a_idx


@pytest.mark.asyncio
async def test_account_deletion_cascade(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
):
    """Deleting account should remove users."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create account
    resp = await client.post(
        "/api/v1/accounts", 
        json={"name": "Cascade Test"}, 
        headers=headers
    )
    account_id = resp.json()["id"]

    # Inject a user directly into DB linked to this account
    # We need a role first
    from snackbase.infrastructure.persistence.models import RoleModel
    role_res = await db_session.execute(select(RoleModel).limit(1))
    role = role_res.scalar_one()

    user = UserModel(
        id="user_cascade_test",
        email="cascade@test.com",
        account_id=account_id,
        role=role,
        password_hash="hash"
    )
    db_session.add(user)
    await db_session.commit()

    # Delete Account via API
    resp = await client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
    assert resp.status_code == 204

    # Verify user is gone from DB
    user_check = await db_session.get(UserModel, "user_cascade_test")
    assert user_check is None


@pytest.mark.asyncio
async def test_non_superadmin_access_denied(
    client: AsyncClient, regular_user_token: str
):
    """Regular users get 403."""
    headers = {"Authorization": f"Bearer {regular_user_token}"}

    # List
    resp = await client.get("/api/v1/accounts", headers=headers)
    assert resp.status_code == 403

    # Create
    resp = await client.post("/api/v1/accounts", json={"name": "Hacker"}, headers=headers)
    assert resp.status_code == 403

    # Delete (try to delete system account for fun)
    resp = await client.delete("/api/v1/accounts/SY0000", headers=headers)
    assert resp.status_code == 403
