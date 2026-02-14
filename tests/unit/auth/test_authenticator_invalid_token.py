import pytest
from unittest.mock import patch
from snackbase.infrastructure.auth.authenticator import Authenticator, AuthenticationError
from snackbase.infrastructure.auth.jwt_service import InvalidTokenError

@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret")

@pytest.mark.asyncio
async def test_authenticate_no_header(authenticator):
    """Test that authentication fails if no credentials are provided."""
    with pytest.raises(AuthenticationError, match="Missing authentication credentials"):
        await authenticator.authenticate({})

@pytest.mark.asyncio
async def test_authenticate_unknown_prefix_in_bearer(authenticator):
    """Test that unknown prefixes in Bearer tokens are treated as JWTs and fail if invalid."""
    token = "unknown_prefix.payload.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", side_effect=InvalidTokenError("Invalid JWT")):
        with pytest.raises(AuthenticationError, match="Invalid JWT"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"})

@pytest.mark.asyncio
async def test_authenticate_invalid_jwt(authenticator):
    """Test that invalid JWT tokens are rejected."""
    token = "invalid.jwt.token"
    
    with patch("snackbase.infrastructure.auth.authenticator.jwt_service.validate_access_token", side_effect=InvalidTokenError("Signature verification failed")):
        with pytest.raises(AuthenticationError, match="Signature verification failed"):
            await authenticator.authenticate({"Authorization": f"Bearer {token}"})

@pytest.mark.asyncio
async def test_authenticate_malformed_api_key_header(authenticator):
    """Test that malformed tokens in X-API-Key header are rejected."""
    token = "malformed_token"
    
    with pytest.raises(AuthenticationError, match="Invalid API key format"):
        await authenticator.authenticate({"X-API-Key": token})

@pytest.mark.asyncio
async def test_authenticate_sb_token_invalid_signature(authenticator):
    """Test that SnackBase tokens with invalid signatures are rejected."""
    token = "sb_ak.payload.invalidsig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", side_effect=AuthenticationError("Invalid token signature")):
        with pytest.raises(AuthenticationError, match="Invalid token signature"):
            await authenticator.authenticate({"X-API-Key": token})
