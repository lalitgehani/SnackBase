import pytest
from httpx import AsyncClient
from snackbase.infrastructure.persistence.models import APIKeyModel
from snackbase.infrastructure.auth import api_key_service

@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, superadmin_token, db_session):
    response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "New Automation Key"},
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Automation Key"
    assert "key" in data
    assert data["key"].startswith("sb_ak.")
    assert len(data["key"]) > 100 # JWT-like keys are much longer
    
    # Verify it's stored in DB (hashed)
    key_hash = api_key_service.hash_key(data["key"])
    from sqlalchemy import select
    result = await db_session.execute(select(APIKeyModel).where(APIKeyModel.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    assert api_key is not None
    assert api_key.name == "New Automation Key"

@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, superadmin_token, db_session):
    # Setup: Create some keys
    key1 = APIKeyModel(
        id="key-1", name="Key 1", key_hash="hash1", 
        user_id="superadmin", account_id="00000000-0000-0000-0000-000000000000"
    )
    key2 = APIKeyModel(
        id="key-2", name="Key 2", key_hash="hash2", 
        user_id="superadmin", account_id="00000000-0000-0000-0000-000000000000",
        is_active=False
    )
    db_session.add_all([key1, key2])
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # Check masking
    item1 = next(k for k in data["items"] if k["id"] == "key-1")
    assert item1["key"] == api_key_service.mask_key("hash1")
    assert item1["is_active"] is True

@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, superadmin_token, db_session):
    # Setup: Create a key
    key = APIKeyModel(
        id="revoke-me", name="Revoke Me", key_hash="hash-to-revoke", 
        user_id="superadmin", account_id="00000000-0000-0000-0000-000000000000"
    )
    db_session.add(key)
    await db_session.commit()
    
    response = await client.delete(
        "/api/v1/admin/api-keys/revoke-me",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    assert response.status_code == 204
    
    # Verify soft delete
    await db_session.refresh(key)
    assert key.is_active is False

@pytest.mark.asyncio
async def test_api_keys_restricted_to_superadmin(client: AsyncClient, regular_user_token):
    response = await client.get(
        "/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    # Regular user should be forbidden
    assert response.status_code == 403
