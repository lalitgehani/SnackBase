import base64
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from snackbase.infrastructure.auth.authenticator import Authenticator
from snackbase.infrastructure.auth.token_codec import AuthenticationError, TokenCodec
from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType
from snackbase.infrastructure.persistence.models import TokenBlacklistModel


@pytest.fixture
def secret():
    return "test-secret-key-12345"


@pytest.fixture
def another_secret():
    return "different-secret-key-67890"


@pytest.fixture
def authenticator(secret):
    return Authenticator(secret=secret)


@pytest.fixture
def token_payload():
    now = int(time.time())
    return TokenPayload(
        type=TokenType.API_KEY,
        user_id=str(uuid.uuid4()),
        email="test@example.com",
        account_id=str(uuid.uuid4()),
        role="admin",
        permissions=["read", "write"],
        issued_at=now,
        expires_at=now + 3600,
        token_id=str(uuid.uuid4()),
    )


def test_token_signature_forgery_fails(token_payload, secret, another_secret):
    """Verifies that a token signed with a different secret is rejected."""
    # Encode with one secret
    token = TokenCodec.encode(token_payload, secret=another_secret)

    # Try to decode with the correct secret
    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        TokenCodec.decode(token, secret=secret)


def test_token_tampering_fails(token_payload, secret):
    """Verifies that tampering with the payload invalidates the signature."""
    # Create valid token
    valid_token = TokenCodec.encode(token_payload, secret=secret)
    parts = valid_token.split(".")
    assert len(parts) == 3
    prefix, payload_segment, signature_segment = parts

    # Decode payload, modify it, and re-encode
    payload_json = base64.urlsafe_b64decode(payload_segment + "==").decode("utf-8")
    payload_data = json.loads(payload_json)
    payload_data["role"] = "superadmin"  # Elevate privilege
    
    modified_payload_json = json.dumps(payload_data)
    modified_payload_segment = base64.urlsafe_b64encode(
        modified_payload_json.encode("utf-8")
    ).rstrip(b"=").decode("ascii")

    # Reconstruct token with modified payload but original signature
    forged_token = f"{prefix}.{modified_payload_segment}.{signature_segment}"

    # Verify rejection
    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        TokenCodec.decode(forged_token, secret=secret)


@pytest.mark.asyncio
async def test_expired_token_rejected(authenticator, secret):
    """Verifies that an expired token is rejected."""
    now = int(time.time())
    expired_payload = TokenPayload(
        type=TokenType.API_KEY,
        user_id=str(uuid.uuid4()),
        email="expired@example.com",
        account_id=str(uuid.uuid4()),
        role="user",
        issued_at=now - 7200,  # Issued 2 hours ago
        expires_at=now - 3600, # Expired 1 hour ago
        token_id=str(uuid.uuid4()),
    )

    token = TokenCodec.encode(expired_payload, secret=secret)

    with pytest.raises(AuthenticationError, match="Token has expired"):
        await authenticator.authenticate(
            {"X-API-Key": token}, session=None
        )


@pytest.mark.asyncio
async def test_wrong_secret_fails(token_payload, another_secret):
    """Verifies that Authenticator initialized with wrong secret rejects valid tokens."""
    # Authenticator with WRONG secret
    auth = Authenticator(secret="wrong-secret")
    
    # Token signed with CORRECT (another) secret
    token = TokenCodec.encode(token_payload, secret=another_secret)

    with pytest.raises(AuthenticationError, match="Invalid token signature"):
        await auth.authenticate({"X-API-Key": token}, session=None)


@pytest.mark.asyncio
async def test_blacklisted_token_rejected(authenticator, secret, db_session, token_payload):
    """Verifies that a blacklisted token is rejected."""
    # 1. Create a valid token
    token = TokenCodec.encode(token_payload, secret=secret)
    
    # 2. Add token to blacklist
    blacklist_entry = TokenBlacklistModel(
        id=token_payload.token_id,
        token_type=token_payload.type,
        revoked_at=int(time.time()),
        reason="Compromised",
    )
    db_session.add(blacklist_entry)
    await db_session.commit()
    
    # 3. Authenticate and expect revocation error
    with pytest.raises(AuthenticationError, match="Token has been revoked"):
        await authenticator.authenticate({"X-API-Key": token}, session=db_session)
