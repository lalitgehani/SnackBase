import pytest
import pytest_asyncio
import uuid
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
from snackbase.infrastructure.persistence.models import AccountModel, UserModel, RoleModel
from tests.security.conftest import AttackClient

@pytest_asyncio.fixture
async def isolation_test_data(db_session: AsyncSession):
    """Setup data for isolation testing: Two accounts with records and users."""
    # 1. Create Account A and User A
    account_a = AccountModel(
        id="AC0001",
        account_code="AC0001",
        name="Account A",
        slug="account-a"
    )
    db_session.add(account_a)
    
    # 2. Create Account B and User B
    account_b = AccountModel(
        id="AC0002",
        account_code="AC0002",
        name="Account B",
        slug="account-b"
    )
    db_session.add(account_b)
    
    # Get roles
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "user"))
    user_role = result.scalar_one()
    result = await db_session.execute(select(RoleModel).where(RoleModel.name == "admin"))
    admin_role = result.scalar_one()

    # User A
    user_a = UserModel(
        id="user-a",
        email="user-a@example.com",
        account_id=account_a.id,
        password_hash="hashed",
        role_id=user_role.id,
        is_active=True
    )
    db_session.add(user_a)
    
    # User B
    user_b = UserModel(
        id="user-b",
        email="user-b@example.com",
        account_id=account_b.id,
        password_hash="hashed",
        role_id=user_role.id,
        is_active=True
    )
    db_session.add(user_b)
    
    await db_session.commit()
    
    # Tokens
    token_a = jwt_service.create_access_token(
        user_id=user_a.id,
        account_id=user_a.account_id,
        email=user_a.email,
        role="user"
    )
    
    token_b = jwt_service.create_access_token(
        user_id=user_b.id,
        account_id=user_b.account_id,
        email=user_b.email,
        role="user"
    )
    
    return {
        "account_a": account_a,
        "account_b": account_b,
        "user_a_token": token_a,
        "user_b_token": token_b
    }

@pytest_asyncio.fixture
async def isolation_collection(client: AsyncClient, superadmin_token, isolation_test_data):
    """Create a collection for isolation testing."""
    collection_name = f"secrets_{uuid.uuid4().hex[:8]}"
    
    collection_data = {
        "name": collection_name,
        "schema": [
            {"name": "title", "type": "text", "required": True},
            {"name": "secret_data", "type": "text", "required": True},
        ],
    }
    
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    response = await client.post("/api/v1/collections", json=collection_data, headers=headers)
    assert response.status_code == 201
    
    # Grant permissions to 'user' role for this collection
    permission_data = {
        "role_id": 2, # user role
        "collection": collection_name,
        "rules": {
            "create": {"rule": "true", "fields": "*"},
            "read": {"rule": "true", "fields": "*"},
            "update": {"rule": "true", "fields": "*"},
            "delete": {"rule": "true", "fields": "*"},
        },
    }
    await client.post("/api/v1/permissions", json=permission_data, headers=headers)
    
    return collection_name

@pytest.mark.asyncio
async def test_iso_ac_001_user_a_sees_own_records(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-001: User A sees their own records."""
    headers = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    
    # 1. Create record as User A
    record_data = {"title": "A's Secret", "secret_data": "shhh"}
    create_resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json=record_data, 
        headers=headers,
        description="User A creates a record"
    )
    assert create_resp.status_code == 201
    
    # 2. List records
    list_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}", 
        headers=headers,
        description="User A lists records"
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "A's Secret"

@pytest.mark.asyncio
async def test_iso_ac_002_user_a_cannot_see_account_b_records(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-002: User A cannot see Account B's records."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    
    # 1. Create record as User B
    record_b = {"title": "B's Secret", "secret_data": "don't look"}
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json=record_b, 
        headers=headers_b,
        description="User B creates a record"
    )
    
    # 2. List as User A
    list_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}", 
        headers=headers_a,
        description="User A lists records (should not see B's)"
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    
    # Verify User A doesn't see User B's record
    titles = [item["title"] for item in data["items"]]
    assert "B's Secret" not in titles

@pytest.mark.asyncio
async def test_iso_ac_003_user_a_cannot_access_b_record_by_id(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-003: User A cannot access B's record by ID (404 Not Found)."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    
    # 1. Create record as User B
    resp_b = await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "B's ID Secret", "secret_data": "prying eyes"}, 
        headers=headers_b
    )
    record_id_b = resp_b.json()["id"]
    
    # 2. Try to GET as User A
    get_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}/{record_id_b}",
        headers=headers_a,
        description="User A attempts to access B's record by ID"
    )
    
    # Should be 404 (or 403, but 404 is better for isolation to avoid leaking existence)
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_iso_ac_004_user_a_cannot_update_b_record(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-004: User A cannot update B's record."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    
    # 1. Create record as User B
    resp_b = await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "B's Update Secret", "secret_data": "pre-hack"}, 
        headers=headers_b
    )
    record_id_b = resp_b.json()["id"]
    
    # 2. Try to UPDATE as User A
    update_resp = await attack_client.patch(
        f"/api/v1/records/{isolation_collection}/{record_id_b}",
        json={"title": "Hacked Title"},
        headers=headers_a,
        description="User A attempts to update B's record"
    )
    
    assert update_resp.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_iso_ac_005_user_a_cannot_delete_b_record(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-005: User A cannot delete B's record."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    
    # 1. Create record as User B
    resp_b = await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "B's Delete Secret", "secret_data": "delete me not"}, 
        headers=headers_b
    )
    record_id_b = resp_b.json()["id"]
    
    # 2. Try to DELETE as User A
    delete_resp = await attack_client.delete(
        f"/api/v1/records/{isolation_collection}/{record_id_b}",
        headers=headers_a,
        description="User A attempts to delete B's record"
    )
    
    assert delete_resp.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_iso_ac_006_user_a_cannot_create_in_b_account(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-006: User A cannot create a record with B's account_id."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    # Try to inject B's account_id
    record_data = {
        "title": "A's Injection", 
        "secret_data": "stealth",
        "account_id": acc_b_id # Attack vector: injecting other account_id
    }
    
    resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json=record_data, 
        headers=headers_a,
        description="User A attempts to create record in Account B"
    )
    
    # Should be 422 Unprocessable Content because account_id is a system field 
    # and shouldn't be allowed in the request body at all.
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "account_id" in resp.json()["detail"]["unauthorized_fields"]

@pytest.mark.asyncio
async def test_iso_ac_007_superadmin_sees_all_records(
    attack_client: AttackClient, 
    superadmin_token, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-007: Superadmin sees all records across accounts."""
    sa_headers = {"Authorization": f"Bearer {superadmin_token}"}
    h_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    h_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    
    # 1. Create record in A
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "Record A", "secret_data": "data a"}, 
        headers=h_a
    )
    
    # 2. Create record in B
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "Record B", "secret_data": "data b"}, 
        headers=h_b
    )
    
    # 3. List as Superadmin
    list_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}", 
        headers=sa_headers,
        description="Superadmin lists all records"
    )
    
    assert list_resp.status_code == 200
    data = list_resp.json()
    
    # Verify both records are visible
    titles = [item["title"] for item in data["items"]]
    assert "Record A" in titles
    assert "Record B" in titles

@pytest.mark.asyncio
async def test_iso_ac_008_filter_bypass_attempt(
    attack_client: AttackClient, 
    isolation_test_data, 
    isolation_collection
):
    """ISO-AC-008: Attempt to bypass isolation via account_id query param."""
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    acc_b_id = isolation_test_data["account_b"].id
    
    # 1. Create record as B
    h_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}", 
        json={"title": "B's Filter Secret", "secret_data": "hidden"}, 
        headers=h_b
    )
    
    # 2. List as A with account_id filter targeting B
    list_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}?account_id={acc_b_id}", 
        headers=headers_a,
        description="User A attempts filter bypass via ?account_id=B"
    )
    
    assert list_resp.status_code == 200
    data = list_resp.json()
    
    # Verify User A doesn't see User B's record even with the filter
    titles = [item["title"] for item in data["items"]]
    assert "B's Filter Secret" not in titles
