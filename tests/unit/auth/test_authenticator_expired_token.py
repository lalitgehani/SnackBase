import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenType, TokenPayload
from snackbase.infrastructure.auth.jwt_service import TokenExpiredError

@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret")

@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncMock)
    session.execute = AsyncMock()
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
        issued_at=int(time.time()) - 7200,
        expires_at=int(time.time()) - 3600, # Expired 1 hour ago
        token_id="tok_789"
    )

@pytest.mark.asyncio
async def test_authenticate_expired_jwt(authenticator):
    """Test that expired JWT tokens are rejected."""
    token = "expired.jwt.token"
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", side_effect=TokenExpiredError("Token expired")):
        with pytest.raises(AuthenticationError, match="Token expired"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"})

@pytest.mark.asyncio
async def test_authenticate_expired_sb_token(authenticator, sample_payload):
    """Test that expired SnackBase tokens are rejected."""
    token = "sb_ak.expired.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        with pytest.raises(AuthenticationError, match="Token has expired"):
            await authenticator.authenticate({"X-API-Key": token})

@pytest.mark.asyncio
async def test_authenticate_expired_legacy_api_key(authenticator, mock_session):
    """Test that expired legacy API keys are rejected."""
    token = "sb_sk_EXPIRED"
    
    mock_key = MagicMock()
    # Expired 1 hour ago
    mock_key.expires_at = datetime.now(timezone.utc).replace(year=2020)
    mock_key.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_key
    mock_session.execute.return_value = mock_result

    with pytest.raises(AuthenticationError, match="API key has expired"):
        await authenticator.authenticate({"X-API-Key": token}, session=mock_session)
