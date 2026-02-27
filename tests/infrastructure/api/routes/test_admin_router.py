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
    superadmin_token: str,
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
    
    response = await client.get(
        "/api/v1/admin/configuration/stats",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
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
    superadmin_token: str,
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
    
    response = await client.get(
        "/api/v1/admin/configuration/recent?limit=5",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) > 0
    # Find our config
    found = next((c for c in data if c["id"] == config_id), None)
    assert found is not None
    assert found["display_name"] == "Test Storage"

@pytest.mark.asyncio
async def test_get_system_configurations(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test getting system configurations."""
    # Setup test data
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    # Ensure system account exists
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

    # Create system config
    sys_config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_sys_list",
        display_name="Test System List",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True
    )
    
    # Create account config (should not be returned)
    acc_config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="acc_123",
        category="auth_providers",
        provider_name="test_acc_list",
        display_name="Test Account List",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=False
    )
    
    db_session.add(sys_config)
    db_session.add(acc_config)
    await db_session.commit()
    
    # Test listing all
    response = await client.get(
        "/api/v1/admin/configuration/system",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Check if system config is present and account config is not (by iterating)
    sys_ids = [c["id"] for c in data]
    assert sys_config.id in sys_ids
    assert acc_config.id not in sys_ids
    
    # Test filtering
    response = await client.get(
        "/api/v1/admin/configuration/system?category=auth_providers",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(c["category"] == "auth_providers" for c in data)

@pytest.mark.asyncio
async def test_get_account_configurations(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test getting account configurations."""
    # Setup test data
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    # Create account
    account = AccountModel(
        id="acc_specific",
        account_code="SA0002",
        name="Specific Account",
        slug="specific-account"
    )
    db_session.add(await db_session.merge(account))
    await db_session.flush()

    # Create account config
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="auth_providers",
        provider_name="test_acc_spec",
        display_name="Test Account Specific",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=False
    )
    
    db_session.add(config)
    await db_session.commit()
    
    response = await client.get(
        f"/api/v1/admin/configuration/account?account_id={account.id}",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["provider_name"] == "test_acc_spec"

@pytest.mark.asyncio
async def test_update_configuration_status(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test enabling/disabling configuration."""
    # Setup test data
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_toggle",
        display_name="Test Toggle",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True
    )
    
    db_session.add(config)
    await db_session.commit()
    
    # Disable
    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    
    # Verify in DB
    await db_session.refresh(config)
    assert config.enabled is False
    
    # Enable
    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True

@pytest.mark.asyncio
async def test_delete_configuration(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test deleting configuration."""
    # Setup test data
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    # Custom config (can delete)
    custom_config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_delete_custom",
        display_name="Test Custom Delete",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True,
        is_builtin=False
    )
    
    # Built-in config (cannot delete)
    builtin_config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_delete_builtin",
        display_name="Test Builtin Delete",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True,
        is_builtin=True
    )
    
    db_session.add(custom_config)
    db_session.add(builtin_config)
    await db_session.commit()
    
    # Delete built-in (should fail)
    response = await client.delete(
        f"/api/v1/admin/configuration/{builtin_config.id}",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 400
    
    # Delete custom (should succeed)
    response = await client.delete(
        f"/api/v1/admin/configuration/{custom_config.id}",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    
    # Verify deletion
    repo = ConfigurationRepository(db_session)
    assert await repo.get_by_id(custom_config.id) is None
    assert await repo.get_by_id(builtin_config.id) is not None

@pytest.mark.asyncio
async def test_set_configuration_default_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test setting a configuration as default via endpoint."""
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_default",
        display_name="Test Default",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True
    )
    db_session.add(config)
    await db_session.commit()
    
    response = await client.post(
        f"/api/v1/admin/configuration/{config.id}/set-default",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True
    
    await db_session.refresh(config)
    assert config.is_default is True

@pytest.mark.asyncio
async def test_unset_configuration_default_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test unsetting a configuration as default via endpoint."""
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_unset_default",
        display_name="Test Unset Default",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True,
        is_default=True
    )
    db_session.add(config)
    await db_session.commit()
    
    response = await client.delete(
        f"/api/v1/admin/configuration/{config.id}/set-default",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is False
    
    await db_session.refresh(config)
    assert config.is_default is False

@pytest.mark.asyncio
async def test_disable_clears_default(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test that disabling a configuration clears its default status."""
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id="00000000-0000-0000-0000-000000000000",
        category="auth_providers",
        provider_name="test_disable_clears",
        display_name="Test Disable Clears",
        config=enc_service.encrypt_dict({"foo": "bar"}),
        enabled=True,
        is_system=True,
        is_default=True
    )
    db_session.add(config)
    await db_session.commit()
    
    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["is_default"] is False
    
    await db_session.refresh(config)
    assert config.enabled is False
    assert config.is_default is False


@pytest.mark.asyncio
async def test_create_storage_configuration_rejects_account_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Storage providers are system-level only and cannot be created for accounts."""
    account = AccountModel(
        id="acc_storage_scope",
        account_code="ST0001",
        name="Storage Scope Account",
        slug="storage-scope-account",
    )
    db_session.add(await db_session.merge(account))
    await db_session.commit()

    response = await client.post(
        "/api/v1/admin/configuration",
        json={
            "category": "storage_providers",
            "provider_name": "s3",
            "display_name": "S3 Account Storage",
            "account_id": account.id,
            "config": {
                "bucket": "bucket",
                "region": "us-east-1",
                "access_key_id": "key",
                "secret_access_key": "secret",
            },
        },
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert response.status_code == 400
    assert "system level" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_account_level_storage_configuration_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Account-level storage configs cannot be updated via admin endpoints."""
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    account = AccountModel(
        id="acc_storage_update",
        account_code="ST0002",
        name="Storage Update Account",
        slug="storage-update-account",
    )
    db_session.add(await db_session.merge(account))
    await db_session.flush()

    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="storage_providers",
        provider_name="s3",
        display_name="S3 Account Storage",
        config=enc_service.encrypt_dict(
            {
                "bucket": "bucket",
                "region": "us-east-1",
                "access_key_id": "key",
                "secret_access_key": "secret",
            }
        ),
        enabled=True,
        is_system=False,
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 400
    assert "system level" in response.json()["detail"].lower()

    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}/values",
        json={"bucket": "new-bucket"},
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 400
    assert "system level" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_set_default_account_level_storage_configuration_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Account-level storage configs cannot be marked default."""
    enc_service = EncryptionService("test-key-must-be-32-bytes-long!!!!")
    account = AccountModel(
        id="acc_storage_default",
        account_code="ST0003",
        name="Storage Default Account",
        slug="storage-default-account",
    )
    db_session.add(await db_session.merge(account))
    await db_session.flush()

    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        category="storage_providers",
        provider_name="s3",
        display_name="S3 Account Storage",
        config=enc_service.encrypt_dict(
            {
                "bucket": "bucket",
                "region": "us-east-1",
                "access_key_id": "key",
                "secret_access_key": "secret",
            }
        ),
        enabled=True,
        is_system=False,
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/configuration/{config.id}/set-default",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert response.status_code == 400
    assert "system level" in response.json()["detail"].lower()
