
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenType, AuthenticatedUser

@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret")

@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncMock)
    session.execute = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_authenticate_jwt_success(authenticator, mock_session):
    """Test successful JWT authentication."""
    token = "valid.jwt.token"
    payload = {
        "user_id": "usr_123",
        "account_id": "acc_456",
        "email": "test@example.com",
        "role": "admin"
    }
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", return_value=payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        mock_session.execute.return_value = mock_result

        user = await authenticator.authenticate({"Authorization": f"Bearer {token}"}, session=mock_session)
        
        assert isinstance(user, AuthenticatedUser)
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.JWT
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.groups == []

@pytest.mark.asyncio
async def test_authenticate_jwt_user_verification_fails(authenticator, mock_session):
    """Test failed user verification during JWT authentication."""
    token = "valid.jwt.token"
    payload = {
        "user_id": "usr_123",
        "account_id": "acc_456",
        "email": "test@example.com",
        "role": "admin"
    }
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", return_value=payload):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(AuthenticationError, match="User does not belong to the specifying account"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"}, session=mock_session)
