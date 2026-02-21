import pytest
from unittest.mock import AsyncMock, MagicMock
from snackbase.infrastructure.persistence.repositories.configuration_repository import ConfigurationRepository
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def repository(mock_session):
    return ConfigurationRepository(mock_session)

@pytest.mark.asyncio
async def test_create_config(repository, mock_session):
    config = ConfigurationModel(
        id="CFG1",
        account_id="ACC1",
        category="auth",
        provider_name="google",
        display_name="Google",
        config={"key": "val"}
    )
    
    result = await repository.create(config)
    
    assert result == config
    mock_session.add.assert_called_with(config)
    mock_session.flush.assert_called()

@pytest.mark.asyncio
async def test_get_by_id(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.get_by_id("CFG1")
    
    assert result == mock_model
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_get_config(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.get_config("auth", "ACC1", "google", is_system=False)
    
    assert result == mock_model
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_list_configs(repository, mock_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [MagicMock(spec=ConfigurationModel)]
    mock_session.execute.return_value = mock_result
    
    result = await repository.list_configs(category="auth", enabled_only=True)
    
    assert len(result) == 1
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_update_config(repository, mock_session):
    config = MagicMock(spec=ConfigurationModel)
    
    result = await repository.update(config)
    
    assert result == config
    mock_session.flush.assert_called()
    mock_session.refresh.assert_called_with(config)

@pytest.mark.asyncio
async def test_delete_config(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.delete("CFG1")
    
    assert result is True
    mock_session.delete.assert_called_with(mock_model)
    mock_session.flush.assert_called()

@pytest.mark.asyncio
async def test_get_default_config(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.get_default_config("auth", "ACC1")
    
    assert result == mock_model
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_set_default_config_success(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_model.enabled = True
    
    # Mock get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.set_default_config("CFG1", "auth", "ACC1", False)
    
    assert result == mock_model
    assert mock_model.is_default is True
    # Verify execute was called twice (one for update, one for get_by_id)
    assert mock_session.execute.call_count == 2
    mock_session.flush.assert_called()

@pytest.mark.asyncio
async def test_set_default_config_disabled_error(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_model.enabled = False
    mock_model.provider_name = "test_provider"
    
    # Mock get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(ValueError, match="Cannot set disabled provider 'test_provider' as default"):
        await repository.set_default_config("CFG1", "auth", "ACC1", False)

@pytest.mark.asyncio
async def test_unset_default_config(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    
    # Mock get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.unset_default_config("CFG1")
    
    assert result is True
    assert mock_model.is_default is False
    mock_session.flush.assert_called()
