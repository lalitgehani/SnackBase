import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.repositories.configuration_repository import ConfigurationRepository
from snackbase.infrastructure.security.encryption import EncryptionService
import uuid

@pytest.mark.asyncio
async def test_get_configuration_stats(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting configuration statistics."""
    # Setup test data
    repo = ConfigurationRepository(db_session)
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    # Clean up existing configs to have deterministic stats
    # (In a real test env, we should rely on isolation, but for now we trust session rollback or cleanup)
    # Actually, we can just assert that the numbers are at least what we create.
    
    # Create accounts
    system_account = AccountModel(
        id="00000000-0000-0000-0000-000000000000",
        account_code="SY0000",
        name="System Account",
        slug="system"
    )
    user_account = AccountModel(
        id="acc_123",
        account_code="UA0001",
        name="User Account",
        slug="user-account"
    )
    db_session.add(await db_session.merge(system_account))
    db_session.add(await db_session.merge(user_account))
    await db_session.flush()

    # Create system config (Auth)
    config1 = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_sys_auth",
        display_name="Test System Auth",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True
    )
    
    # Create account config (Email)
    config2 = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="acc_123",
        category="email_providers",
        provider_name="test_acc_email",
        display_name="Test Account Email",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=False
    )
    
    db_session.add(config1)
    db_session.add(config2)
    await db_session.commit()
    
    response = await client.get("/api/v1/admin/configuration/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "system_configs" in data
    assert "account_configs" in data
    assert data["system_configs"]["by_category"]["auth_providers"] >= 1
    assert data["account_configs"]["by_category"]["email_providers"] >= 1

@pytest.mark.asyncio
async def test_get_recent_configurations(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test getting recent configurations."""
    # Setup test data
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    # Ensure system account exists
    system_account = AccountModel(
        id="00000000-0000-0000-0000-000000000000",
        account_code="SY0000",
        name="System Account",
        slug="system"
    )
    db_session.add(await db_session.merge(system_account))
    await db_session.flush()

    # Create a config
    config_id = str(uuid.uuid4())
    config = ConfigurationModel(
        id=config_id,
        account_id="00000000-0000-0000-0000-000000000000",
        category="storage_providers",
        provider_name="test_storage",
        display_name="Test Storage",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True
    )
    
    db_session.add(config)
    await db_session.commit()
    
    response = await client.get("/api/v1/admin/configuration/recent?limit=5")
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) > 0
    # Find our config
    found = next((c for c in data if c["id"] == config_id), None)
    assert found is not None
    assert found["display_name"] == "Test Storage"
