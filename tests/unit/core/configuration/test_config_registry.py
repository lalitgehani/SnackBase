import pytest
from unittest.mock import AsyncMock, MagicMock
import time
from snackbase.core.configuration.config_registry import ConfigurationRegistry, ProviderDefinition
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel

@pytest.fixture
def mock_repo():
    return AsyncMock()

@pytest.fixture
def mock_encryption():
    service = MagicMock()
    # Mock decrypt_dict to just return the data as is for testing
    service.decrypt_dict.side_effect = lambda x: x
    service.encrypt_dict.side_effect = lambda x: x
    return service

@pytest.fixture
def registry(mock_encryption):
    return ConfigurationRegistry(mock_encryption)

@pytest.mark.asyncio
async def test_get_effective_config_account_override(registry, mock_repo):
    # Setup: account-level config exists
    account_id = "ACC123"
    category = "auth_providers"
    provider_name = "google"
    
    config_data = {"client_id": "acc-client"}
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_model.config = config_data
    mock_model.enabled = True
    
    mock_repo.get_config.return_value = mock_model
    
    # Execute
    result = await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    
    # Assert
    assert result == config_data
    mock_repo.get_config.assert_called_with(
        category=category,
        account_id=account_id,
        provider_name=provider_name,
        is_system=False
    )

@pytest.mark.asyncio
async def test_get_effective_config_system_fallback(registry, mock_repo):
    # Setup: account-level config does NOT exist, system-level DOES exist
    account_id = "ACC123"
    category = "auth_providers"
    provider_name = "google"
    
    system_config_data = {"client_id": "system-client"}
    system_model = MagicMock(spec=ConfigurationModel)
    system_model.config = system_config_data
    system_model.enabled = True
    
    # First call returns None (account override), second returns system model
    mock_repo.get_config.side_effect = [None, system_model]
    
    # Execute
    result = await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    
    # Assert
    assert result == system_config_data
    assert mock_repo.get_config.call_count == 2
    mock_repo.get_config.assert_any_call(
        category=category,
        account_id=account_id,
        provider_name=provider_name,
        is_system=False
    )
    mock_repo.get_config.assert_any_call(
        category=category,
        account_id=registry.SYSTEM_ACCOUNT_ID,
        provider_name=provider_name,
        is_system=True
    )

@pytest.mark.asyncio
async def test_get_effective_config_caching(registry, mock_repo):
    # Setup
    account_id = "ACC123"
    category = "auth_providers"
    provider_name = "google"
    
    config_data = {"client_id": "acc-client"}
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_model.config = config_data
    mock_model.enabled = True
    
    mock_repo.get_config.return_value = mock_model
    
    # Execute twice
    result1 = await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    result2 = await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    
    # Assert
    assert result1 == config_data
    assert result2 == config_data
    # Repo should only be called once due to caching
    assert mock_repo.get_config.call_count == 1

@pytest.mark.asyncio
async def test_cache_invalidation_on_update(registry, mock_repo):
    # Setup
    account_id = "ACC123"
    category = "auth_providers"
    provider_name = "google"
    config_id = "CFG1"
    
    config_data1 = {"client_id": "val1"}
    mock_model1 = MagicMock(spec=ConfigurationModel)
    mock_model1.id = config_id
    mock_model1.category = category
    mock_model1.account_id = account_id
    mock_model1.provider_name = provider_name
    mock_model1.config = config_data1
    mock_model1.enabled = True
    
    mock_repo.get_config.return_value = mock_model1
    mock_repo.get_by_id.return_value = mock_model1
    mock_repo.update.return_value = mock_model1
    
    # Populate cache
    await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    assert mock_repo.get_config.call_count == 1
    
    # Update config
    config_data2 = {"client_id": "val2"}
    mock_model2 = MagicMock(spec=ConfigurationModel)
    mock_model2.config = config_data2
    mock_model2.enabled = True
    mock_repo.get_config.return_value = mock_model2
    
    await registry.update_config(config_id, config=config_data2, repository=mock_repo)
    
    # Execute again - should hit repo again
    result = await registry.get_effective_config(category, account_id, provider_name, mock_repo)
    
    assert result == config_data2
    assert mock_repo.get_config.call_count == 2

@pytest.mark.asyncio
async def test_builtin_deletion_failure(registry, mock_repo):
    # Setup
    config_id = "CFG_BUILTIN"
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_model.is_builtin = True
    mock_repo.get_by_id.return_value = mock_model
    
    # Execute & Assert
    with pytest.raises(ValueError, match="Built-in configurations cannot be deleted"):
        await registry.delete_config(config_id, mock_repo)

def test_register_provider_definition(registry):
    # Execute
    registry.register_provider_definition(
        category="auth_providers",
        name="google",
        display_name="Google Auth",
        is_builtin=True
    )
    
    # Assert
    provider = registry.get_provider_definition("auth_providers", "google")
    assert provider is not None
    assert provider.display_name == "Google Auth"
    assert provider.is_builtin is True
    
    providers = registry.list_provider_definitions(category="auth_providers")
    assert len(providers) == 1
    assert providers[0].name == "google"
