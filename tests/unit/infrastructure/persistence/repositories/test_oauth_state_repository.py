import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from snackbase.infrastructure.persistence.repositories.oauth_state_repository import OAuthStateRepository
from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def repository(mock_session):
    return OAuthStateRepository(mock_session)

@pytest.mark.asyncio
async def test_create_state(repository, mock_session):
    state = OAuthStateModel(
        id="STATE1",
        provider_name="google",
        state_token="secure_token",
        redirect_uri="http://localhost/callback",
        expires_at=datetime.now(timezone.utc)
    )
    
    result = await repository.create(state)
    
    assert result == state
    mock_session.add.assert_called_with(state)
    mock_session.flush.assert_called()

@pytest.mark.asyncio
async def test_get_by_id(repository, mock_session):
    mock_model = MagicMock(spec=OAuthStateModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.get_by_id("STATE1")
    
    assert result == mock_model
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_get_by_token(repository, mock_session):
    mock_model = MagicMock(spec=OAuthStateModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.get_by_token("secure_token")
    
    assert result == mock_model
    mock_session.execute.assert_called()

@pytest.mark.asyncio
async def test_delete_state(repository, mock_session):
    mock_model = MagicMock(spec=OAuthStateModel)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    
    result = await repository.delete("STATE1")
    
    assert result is True
    mock_session.delete.assert_called_with(mock_model)
    mock_session.flush.assert_called()

@pytest.mark.asyncio
async def test_delete_expired(repository, mock_session):
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_session.execute.return_value = mock_result
    
    now = datetime.now(timezone.utc)
    count = await repository.delete_expired(now)
    
    assert count == 5
    mock_session.execute.assert_called()
    mock_session.flush.assert_called()
