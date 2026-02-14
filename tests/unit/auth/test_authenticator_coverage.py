import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.token_types import TokenType, TokenPayload

@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncMock)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_authenticate_jwt_generic_error():
    """Test generic exception handling during JWT authentication."""
    authenticator = Authenticator(secret="test-secret")
    token = "valid.jwt.token"
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", side_effect=Exception("Unexpected error")):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"})

@pytest.mark.asyncio
async def test_authenticate_sb_token_generic_error():
    """Test generic exception handling during SnackBase token authentication."""
    authenticator = Authenticator(secret="test-secret")
    token = "sb_ak.payload.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", side_effect=Exception("Unexpected error")):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await authenticator.authenticate({"X-API-Key": token})

@pytest.mark.asyncio
async def test_authenticate_sb_token_no_secret():
    """Test SnackBase token authentication when secret is not provided in __init__."""
    authenticator = Authenticator(secret=None)
    token = "sb_ak.payload.sig"
    
    # We patch where it is IMPORTED from, which is snackbase.core.config
    # Or, since it's imported inside the function, we patch the source.
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode") as mock_decode:
        # Configure mock to return a payload-like object
        mock_payload = MagicMock()
        mock_payload.expires_at = None
        mock_payload.user_id = "user_123"
        mock_payload.account_id = "acc_456"
        mock_payload.email = "test@example.com"
        mock_payload.role = "admin"
        mock_payload.type = TokenType.API_KEY
        mock_decode.return_value = mock_payload

        with patch("snackbase.core.config.get_settings") as mock_get_settings:
             mock_get_settings.return_value.token_secret = "settings-secret"
             await authenticator.authenticate({"X-API-Key": token})
             
             # Verify that decode was called with the secret from settings
             args, _ = mock_decode.call_args
             assert args[1] == "settings-secret"

@pytest.mark.asyncio
async def test_authenticate_legacy_api_key_no_user(mock_session):
    """Test legacy API key where user relation is missing."""
    authenticator = Authenticator(secret="test")
    token = "sb_sk_valid"
    
    mock_key = MagicMock()
    mock_key.user = None
    mock_key.is_active = True
    mock_key.expires_at = None # Not expired
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_key
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(AuthenticationError, match="User associated with API key not found"):
        await authenticator.authenticate({"X-API-Key": token}, session=mock_session)
