import pytest
import uuid
from httpx import AsyncClient
from snackbase.infrastructure.persistence.models import AccountModel
from tests.security.conftest import AttackClient

@pytest.mark.asyncio
async def test_iso_sa_001_superadmin_lists_all_accounts(
    attack_client: AttackClient,
    superadmin_token: str,
    isolation_test_data: dict
):
    """ISO-SA-001: Superadmin lists all accounts."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    
    response = await attack_client.get(
        "/api/v1/accounts",
        headers=headers,
        description="ISO-SA-001: Superadmin listing all accounts"
    )
    
    assert response.status_code == 200
    data = response.json()
    # Accounts API returns { "items": [...], "total": ... }
    accounts = data.get("items", [])
    assert len(accounts) >= 2
    
    account_ids = [a["id"] for a in accounts]
    assert isolation_test_data["account_a"].id in account_ids
    assert isolation_test_data["account_b"].id in account_ids

@pytest.mark.asyncio
async def test_iso_sa_002_superadmin_views_any_account(
    attack_client: AttackClient,
    superadmin_token: str,
    isolation_test_data: dict
):
    """ISO-SA-002: Superadmin views any account."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    account_b_id = isolation_test_data["account_b"].id
    
    response = await attack_client.get(
        f"/api/v1/accounts/{account_b_id}",
        headers=headers,
        description=f"ISO-SA-002: Superadmin viewing account {account_b_id}"
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == account_b_id

@pytest.mark.asyncio
async def test_iso_sa_003_superadmin_lists_all_records(
    attack_client: AttackClient,
    superadmin_token: str,
    isolation_test_data: dict,
    isolation_collection: str
):
    """ISO-SA-003: Superadmin lists all records."""
    # 1. Create a record as User A
    headers_a = {"Authorization": f"Bearer {isolation_test_data['user_a_token']}"}
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json={"title": "Record A", "secret_data": "Top Secret A"},
        headers=headers_a,
        description="Creating record as User A"
    )
    
    # 2. Create a record as User B
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json={"title": "Record B", "secret_data": "Top Secret B"},
        headers=headers_b,
        description="Creating record as User B"
    )
    
    # 3. Superadmin lists records
    headers_sa = {"Authorization": f"Bearer {superadmin_token}"}
    response = await attack_client.get(
        f"/api/v1/records/{isolation_collection}",
        headers=headers_sa,
        description="ISO-SA-003: Superadmin listing all records"
    )
    
    assert response.status_code == 200
    data = response.json()
    # Records API returns { "items": [...], "total": ..., "skip": ..., "limit": ... }
    records = data.get("items", [])
    assert len(records) >= 2
    
    titles = [r["title"] for r in records]
    assert "Record A" in titles
    assert "Record B" in titles

@pytest.mark.asyncio
async def test_iso_sa_004_superadmin_updates_any_record(
    attack_client: AttackClient,
    superadmin_token: str,
    isolation_test_data: dict,
    isolation_collection: str
):
    """ISO-SA-004: Superadmin updates any record."""
    # 1. Create a record as User B
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    create_resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json={"title": "Record B to Update", "secret_data": "Top Secret B"},
        headers=headers_b,
        description="Creating record as User B for update"
    )
    record_id = create_resp.json()["id"]
    
    # 2. Superadmin updates the record (using PATCH for partial update)
    headers_sa = {"Authorization": f"Bearer {superadmin_token}"}
    update_data = {"title": "Updated by Superadmin"}
    response = await attack_client.patch(
        f"/api/v1/records/{isolation_collection}/{record_id}",
        json=update_data,
        headers=headers_sa,
        description=f"ISO-SA-004: Superadmin updating record {record_id} of Account B"
    )
    
    assert response.status_code == 200
    assert response.json()["title"] == "Updated by Superadmin"

@pytest.mark.asyncio
async def test_iso_sa_005_superadmin_deletes_any_record(
    attack_client: AttackClient,
    superadmin_token: str,
    isolation_test_data: dict,
    isolation_collection: str
):
    """ISO-SA-005: Superadmin deletes any record."""
    # 1. Create a record as User B
    headers_b = {"Authorization": f"Bearer {isolation_test_data['user_b_token']}"}
    create_resp = await attack_client.post(
        f"/api/v1/records/{isolation_collection}",
        json={"title": "Record B to Delete", "secret_data": "Top Secret B"},
        headers=headers_b,
        description="Creating record as User B for deletion"
    )
    record_id = create_resp.json()["id"]
    
    # 2. Superadmin deletes the record
    headers_sa = {"Authorization": f"Bearer {superadmin_token}"}
    response = await attack_client.delete(
        f"/api/v1/records/{isolation_collection}/{record_id}",
        headers=headers_sa,
        description=f"ISO-SA-005: Superadmin deleting record {record_id} of Account B"
    )
    
    assert response.status_code == 204
    
    # 3. Verify deletion
    verify_resp = await attack_client.get(
        f"/api/v1/records/{isolation_collection}/{record_id}",
        headers=headers_sa,
        description="Verifying deletion"
    )
    assert verify_resp.status_code == 404

@pytest.mark.asyncio
async def test_iso_sa_006_superadmin_cannot_delete_system_account(
    attack_client: AttackClient,
    superadmin_token: str
):
    """ISO-SA-006: Superadmin cannot delete system account."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    system_account_id = "00000000-0000-0000-0000-000000000000"
    
    response = await attack_client.delete(
        f"/api/v1/accounts/{system_account_id}",
        headers=headers,
        description="ISO-SA-006: Attempting to delete system account"
    )
    
    # Expect 422 because system account is immutable
    assert response.status_code == 422
