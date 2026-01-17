import pytest
from httpx import AsyncClient
from snackbase.infrastructure.persistence.models import APIKeyModel, UserModel
from snackbase.infrastructure.auth import api_key_service
from datetime import datetime, timedelta, UTC

@pytest.fixture
async def superadmin_user(db_session):
    # This fixture should ideally come from a conftest.py or be set up to use the SYSTEM_ACCOUNT_ID
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    from snackbase.infrastructure.persistence.repositories import UserRepository, RoleRepository
    
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    
    role = await role_repo.get_by_name("admin")
    
    user = UserModel(
        id="test-superadmin-id",
        email="superadmin@example.com",
        password_hash="...",
        account_id=SYSTEM_ACCOUNT_ID,
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_api_key_authentication_success(client: AsyncClient, db_session, superadmin_user):
    # Setup: Create a valid API key
    plaintext_key = "sb_sk_SY0000_testkeyrandompart1234567890123"
    key_hash = api_key_service.hash_key(plaintext_key)
    
    api_key = APIKeyModel(
        id="test-key-id",
        name="Test Key",
        key_hash=key_hash,
        user_id=superadmin_user.id,
        account_id=superadmin_user.account_id,
        is_active=True,
    )
    db_session.add(api_key)
    await db_session.commit()
    
    # Test: Access a superadmin-only endpoint using the API key
    response = await client.get(
        "/api/v1/users",
        headers={"X-API-Key": plaintext_key}
    )
    
    assert response.status_code == 200
    
    # Verify last_used_at was updated
    await db_session.refresh(api_key)
    assert api_key.last_used_at is not None

@pytest.mark.asyncio
async def test_api_key_authentication_invalid_key(client: AsyncClient):
    response = await client.get(
        "/api/v1/users",
        headers={"X-API-Key": "sb_sk_SY0000_invalid"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"

@pytest.mark.asyncio
async def test_api_key_authentication_expired_key(client: AsyncClient, db_session, superadmin_user):
    # Setup: Create an expired API key
    plaintext_key = "sb_sk_SY0000_expiredkey"
    key_hash = api_key_service.hash_key(plaintext_key)
    
    api_key = APIKeyModel(
        id="expired-key-id",
        name="Expired Key",
        key_hash=key_hash,
        user_id=superadmin_user.id,
        account_id=superadmin_user.account_id,
        is_active=True,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(api_key)
    await db_session.commit()
    
    # We need to refresh to ensure is_active is loaded and object is attached
    await db_session.refresh(api_key)
    
    response = await client.get(
        "/api/v1/users",
        headers={"X-API-Key": plaintext_key}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "API key has expired"

@pytest.mark.asyncio
async def test_api_key_authentication_inactive_key(client: AsyncClient, db_session, superadmin_user):
    # Setup: Create an inactive API key
    plaintext_key = "sb_sk_SY0000_inactivekey"
    key_hash = api_key_service.hash_key(plaintext_key)
    
    api_key = APIKeyModel(
        id="inactive-key-id",
        name="Inactive Key",
        key_hash=key_hash,
        user_id=superadmin_user.id,
        account_id=superadmin_user.account_id,
        is_active=False,
    )
    db_session.add(api_key)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/users",
        headers={"X-API-Key": plaintext_key}
    )
    assert response.status_code == 401 # Should fail because repository only returns active keys for get_by_hash

@pytest.mark.asyncio
async def test_api_key_authentication_non_superadmin(client: AsyncClient, db_session):
    # Setup: Create a non-superadmin user and an API key for them
    from snackbase.infrastructure.persistence.repositories import UserRepository, RoleRepository, AccountRepository
    
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    account_repo = AccountRepository(db_session)
    
    # Create an account if "default" doesn't exist
    from snackbase.infrastructure.persistence.models import AccountModel
    account = await account_repo.get_by_slug("default")
    if not account:
        account = AccountModel(
            id="test-normal-account-id",
            name="Default Account",
            slug="default",
            account_code="DE0000"
        )
        db_session.add(account)
        await db_session.flush()
    
    role = await role_repo.get_by_name("admin")
    
    user = UserModel(
        id="test-normal-admin-id",
        email="admin@example.com",
        password_hash="...",
        account_id=account.id,
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    
    plaintext_key = "sb_sk_DE0000_normaladmin"
    key_hash = api_key_service.hash_key(plaintext_key)
    
    api_key = APIKeyModel(
        id="normal-key-id",
        name="Normal Key",
        key_hash=key_hash,
        user_id=user.id,
        account_id=user.account_id,
        is_active=True,
    )
    db_session.add(api_key)
    await db_session.commit()
    
    response = await client.get(
        "/api/v1/users",
        headers={"X-API-Key": plaintext_key}
    )
    # The dependency specifically checks for SYSTEM_ACCOUNT_ID for API keys
    assert response.status_code == 403
    assert response.json()["detail"] == "API keys are restricted to superadmin users"
