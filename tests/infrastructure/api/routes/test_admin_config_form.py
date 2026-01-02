import pytest
import pytest_asyncio
from httpx import AsyncClient
from snackbase.core.configuration.config_registry import ConfigurationRegistry, ProviderDefinition
from snackbase.infrastructure.persistence.repositories.configuration_repository import ConfigurationRepository
from snackbase.infrastructure.security.encryption import EncryptionService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_registry(db_session: AsyncSession):
    """Ensure registry and other state are initialized for tests."""
    from snackbase.infrastructure.api.app import app
    from snackbase.infrastructure.persistence.repositories.configuration_repository import ConfigurationRepository
    
    # Initialize or update the regsitry in app.state
    if not hasattr(app.state, "config_registry"):
        registry = ConfigurationRegistry(
            EncryptionService("test-key-must-be-32-bytes-long!!!!")
        )
        app.state.config_registry = registry
    
    # Clear registry memory state for isolation
    app.state.config_registry._provider_definitions = {}
    app.state.config_registry._cache = {}
    
    # Register email_password in registry (usually done in lifespan)
    from snackbase.infrastructure.configuration.providers.auth.email_password import EmailPasswordProvider
    ep = EmailPasswordProvider()
    app.state.config_registry.register_provider_definition(
        category=ep.category,
        name=ep.provider_name,
        display_name=ep.display_name,
        config_schema=ep.config_schema,
        is_builtin=True
    )
    
    # Seed email_password config if not exists (usually done in lifespan)
    repo = ConfigurationRepository(db_session)
    if not await repo.get_config(ep.category, app.state.config_registry.SYSTEM_ACCOUNT_ID, ep.provider_name, True):
        await app.state.config_registry.create_config(
            account_id=app.state.config_registry.SYSTEM_ACCOUNT_ID,
            category=ep.category,
            provider_name=ep.provider_name,
            display_name=ep.display_name,
            config={},
            is_builtin=True,
            is_system=True,
            repository=repo
        )
    
    return app.state.config_registry

@pytest.mark.asyncio
async def test_email_password_seeded(client: AsyncClient, superadmin_token: str):
    response = await client.get(
        "/api/v1/admin/configuration/system",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    configs = response.json()
    assert any(c["provider_name"] == "email_password" for c in configs)

@pytest.mark.asyncio
async def test_get_available_providers(client: AsyncClient, superadmin_token: str):
    # Mock some providers in registry
    from snackbase.infrastructure.api.app import app
    registry: ConfigurationRegistry = app.state.config_registry
    registry.register_provider_definition(
        category="auth_providers",
        name="test_auth_list",
        display_name="Test Auth",
        config_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
    )

    response = await client.get(
        "/api/v1/admin/configuration/providers",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    providers = response.json()
    assert any(p["name"] == "test_auth_list" for p in providers)

@pytest.mark.asyncio
async def test_get_provider_schema(client: AsyncClient, superadmin_token: str):
    from snackbase.infrastructure.api.app import app
    registry: ConfigurationRegistry = app.state.config_registry
    registry.register_provider_definition(
        category="auth_providers",
        name="test_auth_schema",
        display_name="Test Auth Schema",
        config_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
    )
    response = await client.get(
        "/api/v1/admin/configuration/schema/auth_providers/test_auth_schema",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    schema = response.json()
    assert schema["type"] == "object"
    assert "foo" in schema["properties"]

@pytest.mark.asyncio
async def test_create_configuration(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    data = {
        "category": "auth_providers",
        "provider_name": "test_auth_create",
        "display_name": "My Auth",
        "config": {"foo": "bar"},
        "enabled": True
    }
    response = await client.post(
        "/api/v1/admin/configuration",
        json=data,
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "id" in result
    
    # VERIFY DB PERSISTENCE
    repo = ConfigurationRepository(db_session)
    config = await repo.get_by_id(result["id"])
    assert config is not None
    assert config.provider_name == "test_auth_create"

@pytest.mark.asyncio
async def test_get_and_update_configuration_values(client: AsyncClient, superadmin_token: str, db_session: AsyncSession):
    # Create a config first
    from snackbase.infrastructure.api.app import app
    registry: ConfigurationRegistry = app.state.config_registry
    config = await registry.create_config(
        account_id=registry.SYSTEM_ACCOUNT_ID,
        category="auth_providers",
        provider_name="test_auth_update",
        display_name="Test Config",
        config={"password": "secret_password", "normal": "value"},
        is_system=True,
        repository=ConfigurationRepository(db_session)
    )
    await db_session.commit()

    # Register schema with secret field
    registry.register_provider_definition(
        category="auth_providers",
        name="test_auth_update",
        display_name="Test Auth Update",
        config_schema={
            "type": "object", 
            "properties": {
                "password": {"type": "string", "writeOnly": True},
                "normal": {"type": "string"}
            }
        }
    )

    # Get values (should be masked)
    response = await client.get(
        f"/api/v1/admin/configuration/{config.id}/values",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    values = response.json()
    assert values["password"] == "••••••••"
    assert values["normal"] == "value"

    # Update values (keeping masked secret)
    update_data = {
        "password": "••••••••",
        "normal": "new_value"
    }
    response = await client.patch(
        f"/api/v1/admin/configuration/{config.id}/values",
        json=update_data,
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    
    # Verify values are correctly preserved and updated
    repo = ConfigurationRepository(db_session)
    updated_config = await repo.get_by_id(config.id)
    decrypted = registry.encryption_service.decrypt_dict(updated_config.config)
    assert decrypted["password"] == "secret_password"
    assert decrypted["normal"] == "new_value"

@pytest.mark.asyncio
async def test_test_connection_unsupported(client: AsyncClient, superadmin_token: str):
    data = {
        "category": "auth_providers",
        "provider_name": "unsupported",
        "config": {}
    }
    response = await client.post(
        "/api/v1/admin/configuration/test-connection",
        json=data,
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] == False
    assert "does not support connection testing" in result["message"]
