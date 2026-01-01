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
async def test_delete_config(repository, mock_session):
    mock_model = MagicMock(spec=ConfigurationModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.delete("CFG1")
    
    assert result is True
    mock_session.delete.assert_called_with(mock_model)
    mock_session.flush.assert_called()
