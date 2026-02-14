
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from snackbase.infrastructure.persistence.models import APIKeyModel, UserModel, AuditLogModel
from snackbase.infrastructure.auth import api_key_service
from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID

@pytest.mark.asyncio
@pytest.mark.enable_audit_hooks
async def test_audit_log_with_api_key_creation(client: AsyncClient, db_session):
    """Test that creating a resource with an API key generates an audit log with correct user info."""
    
    # 1. Setup: Create Superadmin and API Key
    from snackbase.infrastructure.persistence.repositories import RoleRepository
    role_repo = RoleRepository(db_session)
    admin_role = await role_repo.get_by_name("admin")
    
    user = UserModel(
        id="test-audit-admin",
        email="audit-admin@example.com",
        password_hash="...",
        account_id=SYSTEM_ACCOUNT_ID,
        role_id=admin_role.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    
    plaintext_key = "sb_sk_SY0000_auditkey123456789012345"
    key_hash = api_key_service.hash_key(plaintext_key)
    
    api_key = APIKeyModel(
        id="test-audit-key",
        name="Audit Test Key",
        key_hash=key_hash,
        user_id=user.id,
        account_id=user.account_id,
        is_active=True,
    )
    db_session.add(api_key)
    await db_session.commit()
    
    # 2. Action: Create a Collection using API Key
    headers = {"X-API-Key": plaintext_key}
    collection_data = {
        "name": "AuditTestCollection",
        "schema": [{"name": "name", "type": "text"}]
    }
    
    response = await client.post(
        "/api/v1/collections",
        json=collection_data,
        headers=headers
    )
    
    assert response.status_code == 201, f"Failed to create collection: {response.text}"
    collection_id = response.json()["id"]
    
    # 3. Verify: Check Audit Log
    # We need to look for the creation of the collection in audit logs
    # The table name for collections is usually 'collections'
    
    result = await db_session.execute(
        select(AuditLogModel)
        .where(AuditLogModel.table_name == "collections")
        .where(AuditLogModel.record_id == collection_id)
        .where(AuditLogModel.operation == "CREATE")
    )
    logs = list(result.scalars().all())
    
    assert len(logs) > 0, "No audit log found for collection creation"
    log = logs[0]
    
    # Check User ID
    assert log.user_id == user.id, f"Expected user_id {user.id}, got {log.user_id}"
    
    # Check Auth Method (if captured in extra_metadata)
    # Note: extra_metadata might be stored as JSON or similar, depending on implementation
    if log.extra_metadata:
        auth_method = log.extra_metadata.get("auth_method")
        assert auth_method == "api_key", f"Expected auth_method 'api_key', got {auth_method}"
