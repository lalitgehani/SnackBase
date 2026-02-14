import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType, AuthenticatedUser
from snackbase.infrastructure.auth.jwt_service import InvalidTokenError, TokenExpiredError


@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret-at-least-256-bits-long-for-security")


@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncMock)
    # Ensure execute is an async mock
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
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
async def test_authenticate_no_header(authenticator):
    """Test that authentication fails if no credentials are provided."""
    with pytest.raises(AuthenticationError, match="Missing authentication credentials"):
        await authenticator.authenticate({})


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
        # Configure mock session to return a valid user verification result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True  # User exists
        mock_session.execute.return_value = mock_result

        user = await authenticator.authenticate({"Authorization": f"Bearer {token}"}, session=mock_session)
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.JWT
        assert user.groups == []


@pytest.mark.asyncio
async def test_authenticate_sb_token_success(authenticator, sample_payload):
    """Test successful SnackBase unified token authentication."""
    token = "sb_ak.encoded.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        user = await authenticator.authenticate({"Authorization": f"Bearer {token}"})
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.API_KEY
        assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_sb_token_expired(authenticator, sample_payload):
    """Test that expired SnackBase tokens are rejected."""
    token = "sb_ak.encoded.sig"
    sample_payload.expires_at = int(time.time()) - 3600
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        with pytest.raises(AuthenticationError, match="Token has expired"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"})


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
    # Mock groups relationship
    mock_group = MagicMock()
    mock_group.name = "group1"
    mock_user.groups = [mock_group]

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
    assert user.groups == ["group1"]


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


@pytest.mark.asyncio
async def test_authenticate_sb_api_key_via_header(authenticator, sample_payload):
    """Test that SnackBase API keys work via X-API-Key header."""
    token = "sb_ak.encoded.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        user = await authenticator.authenticate({"X-API-Key": token})
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.API_KEY
