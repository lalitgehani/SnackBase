import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from snackbase.infrastructure.auth.api_key_service import api_key_service
from snackbase.infrastructure.auth.token_codec import TokenCodec
from snackbase.infrastructure.auth.token_types import TokenType
from snackbase.infrastructure.persistence.models.api_key import APIKeyModel
from snackbase.infrastructure.persistence.models.token_blacklist import TokenBlacklistModel

@pytest.mark.asyncio
async def test_create_api_key():
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
    user_id = "user-123"
    email = "test@example.com"
    account_id = "acc-456"
    role = "admin"
    name = "Test Key"
    
    # Execute
    plaintext_key, model = await api_key_service.create_api_key(
        session=session,
        user_id=user_id,
        email=email,
        account_id=account_id,
        role=role,
        name=name
    )
    
    # Verify plaintext key
    assert plaintext_key.startswith("sb_ak.")
    
    # Verify payload
    # Mocking settings and secret for decoding if needed, 
    # but here we can just check if it's a valid SB token format
    parts = plaintext_key.split(".")
    assert len(parts) == 3
    
    # Verify model
    assert isinstance(model, APIKeyModel)
    assert model.name == name
    assert model.user_id == user_id
    assert model.account_id == account_id
    assert model.id is not None # token_id
    
    # Verify session calls
    session.add.assert_called_once()
    session.flush.assert_called_once()

@pytest.mark.asyncio
async def test_revoke_api_key():
    # Setup
    session = AsyncMock()
    session.add = MagicMock()
    token_id = "token-123"
    reason = "Test revocation"
    
    # Execute
    await api_key_service.revoke_api_key(
        token_id=token_id,
        session=session,
        reason=reason
    )
    
    # Verify session calls
    session.add.assert_called_once()
    args, _ = session.add.call_args
    blacklist_entry = args[0]
    assert isinstance(blacklist_entry, TokenBlacklistModel)
    assert blacklist_entry.id == token_id
    assert blacklist_entry.token_type == TokenType.API_KEY
    assert blacklist_entry.reason == reason

def test_mask_key_new_format():
    key = "sb_ak.eyJ1c2VyX2lkIjoic3JyMTIzNCJ9.signature"
    masked = api_key_service.mask_key(key)
    assert masked == "sb_ak.eyJ1...ture"

def test_mask_key_legacy_or_hash():
    key = "a" * 64 # simulated hash
    masked = api_key_service.mask_key(key)
    assert masked == "aaaaaa...aaaa"

def test_mask_key_short():
    key = "short"
    masked = api_key_service.mask_key(key)
    assert masked == "****"
