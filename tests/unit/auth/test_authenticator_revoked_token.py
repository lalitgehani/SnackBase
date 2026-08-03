import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snackbase.infrastructure.auth.authenticator import AuthenticationError, Authenticator
from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType


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
        issued_at=int(time.time()),
        expires_at=int(time.time()) + 3600,
        token_id="tok_revoked"
    )

@pytest.mark.asyncio
async def test_authenticate_revoked_sb_token(authenticator, sample_payload, mock_session):
    """Test that revoked SnackBase tokens are rejected when checking against blacklist."""
    token = "sb_ak.revoked.sig"

    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        # Mock blacklist check: returns a result (meaning token IS in blacklist)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "tok_revoked"
        mock_session.execute.return_value = mock_result

        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            await authenticator.authenticate({"X-API-Key": token}, session=mock_session)

@pytest.mark.asyncio
async def test_authenticate_not_revoked_sb_token_success(authenticator, sample_payload, mock_session):
    """Test that non-revoked SnackBase tokens are accepted."""
    token = "sb_ak.valid.sig"
    sample_payload.token_id = "tok_valid"

    with patch("snackbase.infrastructure.auth.authenticator.TokenCodec.decode", return_value=sample_payload):
        # Mock blacklist check: returns None (meaning token fails to be found in blacklist)
        mock_result_blacklist = MagicMock()
        mock_result_blacklist.scalar_one_or_none.return_value = None

        # Mock user verification check: returns True
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = True

        # Mock API key scopes load: (scopes, is_active)
        mock_result_scopes = MagicMock()
        mock_result_scopes.one_or_none.return_value = (["records:secrets:read"], True)

        # Mock touch last_used_at
        mock_result_touch = MagicMock()
        mock_result_touch.scalar_one_or_none.return_value = MagicMock()
        mock_session.commit = AsyncMock()

        # Configure side effects for sequential execute calls:
        # 1) revocation 2) user-account 3) scopes 4) touch
        mock_session.execute.side_effect = [
            mock_result_blacklist,
            mock_result_user,
            mock_result_scopes,
            mock_result_touch,
        ]

        user = await authenticator.authenticate({"X-API-Key": token}, session=mock_session)
        assert user.user_id == "usr_123"
        assert user.scopes == ["records:secrets:read"]
        assert user.api_key_id == "tok_valid"
