import pytest
import uuid
import json
from httpx import AsyncClient
from fastapi import status

from tests.security.conftest import AttackClient

@pytest.mark.asyncio
async def test_perm_rb_001_no_permissions(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name
):
    """PERM-RB-001: User with no permissions cannot create records."""
    token = rbac_users_tokens["no_access"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {"title": "Forbidden Post", "content": "Should fail"}
    
    response = await attack_client.post(
        f"/api/v1/records/{rbac_collection_name}",
        json=payload,
        headers=headers,
        description="User with no permissions attempts to create record"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_perm_rb_002_allow_create(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name
):
    """PERM-RB-002: User with create permission can create records."""
    token = rbac_users_tokens["full_access"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {"title": "Allowed Post", "content": "Should succeed"}
    
    response = await attack_client.post(
        f"/api/v1/records/{rbac_collection_name}",
        json=payload,
        headers=headers,
        description="User with full permissions creates record"
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Allowed Post"

@pytest.mark.asyncio
async def test_perm_rb_003_deny_read(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name
):
    """PERM-RB-003: User without read permission cannot list records."""
    token = rbac_users_tokens["no_access"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await attack_client.get(
        f"/api/v1/records/{rbac_collection_name}",
        headers=headers,
        description="User with no permissions attempts to list records"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_perm_rb_004_allow_read_only(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name
):
    """PERM-RB-004: User with read-only permission can list records."""
    token = rbac_users_tokens["read_only"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await attack_client.get(
        f"/api/v1/records/{rbac_collection_name}",
        headers=headers,
        description="User with read-only permissions lists records"
    )
    
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
async def test_perm_rb_005_deny_update(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name,
    client: AsyncClient
):
    """PERM-RB-005: User with read-only permission cannot update records."""
    # Setup: Create a record using full_access user first
    setup_token = rbac_users_tokens["full_access"]
    setup_headers = {"Authorization": f"Bearer {setup_token}"}
    setup_res = await client.post(
        f"/api/v1/records/{rbac_collection_name}",
        json={"title": "Original"},
        headers=setup_headers
    )
    assert setup_res.status_code == 201
    record_id = setup_res.json()["id"]
    
    # Test: Read-only user tries to update
    token = rbac_users_tokens["read_only"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await attack_client.patch(
        f"/api/v1/records/{rbac_collection_name}/{record_id}",
        json={"title": "Hacked"},
        headers=headers,
        description="User with read-only permissions attempts to update record"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_perm_rb_006_deny_delete(
    attack_client: AttackClient, 
    rbac_users_tokens, 
    rbac_collection_name,
    client: AsyncClient
):
    """PERM-RB-006: User with read-only permission cannot delete records."""
    # Setup: Create a record
    setup_token = rbac_users_tokens["full_access"]
    setup_headers = {"Authorization": f"Bearer {setup_token}"}
    setup_res = await client.post(
        f"/api/v1/records/{rbac_collection_name}",
        json={"title": "To Delete"},
        headers=setup_headers
    )
    assert setup_res.status_code == 201
    record_id = setup_res.json()["id"]
    
    # Test: Read-only user tries to delete
    token = rbac_users_tokens["read_only"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await attack_client.delete(
        f"/api/v1/records/{rbac_collection_name}/{record_id}",
        headers=headers,
        description="User with read-only permissions attempts to delete record"
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_perm_rb_007_wildcard_collection(
    attack_client: AttackClient, 
    rbac_users_tokens,
    superadmin_token
):
    """PERM-RB-007: User with wildcard permission can access any collection."""
    # 1. Create a NEW collection that is NOT the rbac_collection
    wildcard_target = f"wildcard_target_{uuid.uuid4().hex[:6]}"
    
    sa_headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [{"name": "title", "type": "text"}]
    
    # Create valid collection via API
    await attack_client.post(
        "/api/v1/collections",
        json={"name": wildcard_target, "fields": schema},
        headers=sa_headers
    )

    # 2. Access it with wildcard user
    token = rbac_users_tokens["wildcard"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {"title": "Wildcard Post"}
    
    response = await attack_client.post(
        f"/api/v1/records/{wildcard_target}",
        json=payload,
        headers=headers,
        description="User with wildcard permissions creates record in arbitrary collection"
    )
    
    assert response.status_code == status.HTTP_201_CREATED
