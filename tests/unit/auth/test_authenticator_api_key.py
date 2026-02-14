
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenType, AuthenticatedUser, TokenPayload

@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret")

@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncMock)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def sample_payload():
    return TokenPayload(
        version=1,
        type=TokenType.API_KEY,
        user_id="usr_123",
        email="test@example.com",
        account_id="acc_456",
        role="admin",
        permissions=[],
        issued_at=int(time.time()),
        expires_at=int(time.time()) + 3600,
        token_id="tok_789"
    )

@pytest.mark.asyncio
async def test_authenticate_sb_api_key_header_success(authenticator, sample_payload):
    """Test successful SnackBase API key authentication via X-API-Key."""
    token = "sb_ak.encoded.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        user = await authenticator.authenticate({"X-API-Key": token})
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.API_KEY

@pytest.mark.asyncio
async def test_authenticate_sb_api_key_bearer_success(authenticator, sample_payload):
    """Test successful SnackBase API key authentication via Authorization Bearer."""
    token = "sb_ak.encoded.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        user = await authenticator.authenticate({"Authorization": f"Bearer {token}"})
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.API_KEY

@pytest.mark.asyncio
async def test_authenticate_legacy_api_key_success(authenticator, mock_session):
    """Test successful legacy API key authentication."""
    token = "sb_sk_ACC_RANDOM"
    
    from snackbase.infrastructure.api.dependencies import SYSTEM_ACCOUNT_ID
    mock_user = MagicMock()
    mock_user.id = "usr_123"
    mock_user.account_id = SYSTEM_ACCOUNT_ID
    mock_user.email = "test@example.com"
    mock_user.role.name = "admin"
    mock_user.groups = []

    mock_key = MagicMock()
    mock_key.expires_at = None
    mock_key.is_active = True
    mock_key.user = mock_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_key
    mock_session.execute.return_value = mock_result

    user = await authenticator.authenticate({"X-API-Key": token}, session=mock_session)
    
    assert user.user_id == "usr_123"
    assert user.token_type == TokenType.API_KEY
    assert user.role == "admin"

@pytest.mark.asyncio
async def test_authenticate_legacy_api_key_invalid(authenticator, mock_session):
    """Test that invalid legacy API keys are rejected."""
    token = "sb_sk_INVALID"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(AuthenticationError, match="Invalid API key"):
        await authenticator.authenticate({"X-API-Key": token}, session=mock_session)

@pytest.mark.asyncio
async def test_authenticate_legacy_api_key_no_session(authenticator):
    """Test that legacy keys fail if no session is provided."""
    token = "sb_sk_ACC_RANDOM"
    with pytest.raises(AuthenticationError, match="Authentication requires database session"):
        await authenticator.authenticate({"X-API-Key": token})
