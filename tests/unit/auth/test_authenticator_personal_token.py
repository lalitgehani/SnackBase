import pytest
import time
from unittest.mock import patch
from snackbase.infrastructure.auth.authenticator import Authenticator
from snackbase.infrastructure.auth.token_types import TokenType, TokenPayload

@pytest.fixture
def authenticator():
    return Authenticator(secret="test-secret")

@pytest.fixture
def sample_payload():
    return TokenPayload(
        version=1,
        type=TokenType.PERSONAL_TOKEN,
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
async def test_authenticate_personal_token_success(authenticator, sample_payload):
    """Test successful Personal Access Token authentication."""
    token = "sb_pt.encoded.sig"
    
    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        user = await authenticator.authenticate({"Authorization": f"Bearer {token}"})
        
        assert user.user_id == "usr_123"
        assert user.token_type == TokenType.PERSONAL_TOKEN
        assert user.email == "test@example.com"
