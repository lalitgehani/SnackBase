
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import hashlib

from snackbase.infrastructure.persistence.models import UserModel, EmailVerificationTokenModel, TokenBlacklistModel
from snackbase.infrastructure.auth.jwt_service import jwt_service
from snackbase.infrastructure.auth.token_types import TokenType

@pytest.mark.asyncio
async def test_auth_flow_unified(client: AsyncClient, db_session: AsyncSession):
    """Test the complete unified authentication flow."""
    
    # 1. Setup: Register and Verify User
    register_payload = {
        "email": "unified_auth@example.com",
        "password": "Password123!",
        "account_name": "Unified Auth Corp",
        "account_slug": "unified-auth-corp"
    }
    
    res = await client.post("/api/v1/auth/register", json=register_payload)
    assert res.status_code == 201
    
    # Verify email manually
    known_token = "test_verification_token_unified"
    known_hash = hashlib.sha256(known_token.encode()).hexdigest()
    
    await db_session.execute(
        update(EmailVerificationTokenModel)
        .where(EmailVerificationTokenModel.email == "unified_auth@example.com")
        .values(token_hash=known_hash)
    )
    await db_session.commit()
    
    verify_res = await client.post("/api/v1/auth/verify-email", json={"token": known_token})
    assert verify_res.status_code == 200

    # 2. Test Login (Token Generation)
    login_payload = {
        "email": "unified_auth@example.com",
        "password": "Password123!",
        "account": "unified-auth-corp"
    }
    
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    data = login_res.json()
    token = data["token"]
    assert token is not None
    
    # 3. Test Access with Valid Token
    # We use a protected endpoint. /api/v1/users/me is a good candidate if it exists.
    # If not, we can use /api/v1/auth/me usually or any endpoint requiring auth.
    # Let's check /api/v1/users/me availability or try a known protected endpoint.
    # Based on other tests, let's assume /api/v1/users/me or similar exists.
    # Actually, let's use the client to request a known protected route.
    # In test_auth_login.py there isn't a post-login protected route check.
    # Let's try /api/v1/users/me, or if that fails, we can check a different one.
    # For now, I'll assume /api/v1/users/me exists as it is standard.
    

    
    # 3. Test Access with Valid Token (Standard JWT)
    headers = {"Authorization": f"Bearer {token}"}
    
    # We try /api/v1/users/me. If it doesn't exist, we fall back to /api/v1/accounts/{account_id}
    # But usually /api/v1/auth/me or /api/v1/users/me is the standard.
    # Looking at auth_router.py, there is a GET /me endpoint! 
    # It is @router.get("/me") inside auth_router.
    # The auth router is likely mounted at /api/v1/auth.
    # So the endpoint is /api/v1/auth/me.
    
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "unified_auth@example.com"
    
    # 4. Test Token Revocation (Standard JWT - might not work if JTI missing)
    # The current login implementation uses standard JWTs without JTI for access tokens.
    # So we cannot revoke them by ID. 
    # We skip revocation test for standard JWT access token, or we assert it fails to revoke if we try.
    # However, to test the Unified Auth Revocation feature, we should manually create a Unified Token.
    
    # 5. United Token Flow (Manual Creation to simulate "Unified" Token)
    from snackbase.infrastructure.auth.token_codec import TokenCodec
    from snackbase.infrastructure.auth.token_types import TokenPayload, TokenType
    from snackbase.core.config import get_settings
    
    settings = get_settings()
    token_id = "test_unified_token_id"
    user_id = user_data["user_id"]
    account_id = user_data["account_id"]
    
    payload = TokenPayload(
        version=1,
        type=TokenType.PERSONAL_TOKEN, # or API_KEY, just need a unified type
        user_id=user_id,
        email="unified_auth@example.com",
        account_id=account_id,
        role="admin",
        permissions=[],
        issued_at=int(datetime.now(timezone.utc).timestamp()),
        token_id=token_id
    )
    
    # Encode with TokenCodec
    unified_token = TokenCodec.encode(payload, settings.token_secret)
    # Format: sb_pt.payload.sig
    
    # Test Access
    unified_headers = {"Authorization": f"Bearer {unified_token}"}
    unified_res = await client.get("/api/v1/auth/me", headers=unified_headers)
    assert unified_res.status_code == 200
    
    # Test Revocation
    blacklist_entry = TokenBlacklistModel(
        id=token_id,
        token_type=TokenType.PERSONAL_TOKEN.value,
        revoked_at=int(datetime.now(timezone.utc).timestamp()),
        reason="Unified token revocation test"
    )
    db_session.add(blacklist_entry)
    await db_session.commit()
    
    # Ensure blacklist check happens
    revoked_res = await client.get("/api/v1/auth/me", headers=unified_headers)
    assert revoked_res.status_code == 401
    
    # 6. Test Expired Unified Token
    expired_payload = TokenPayload(
        version=1,
        type=TokenType.PERSONAL_TOKEN,
        user_id=user_id,
        email="unified_auth@example.com",
        account_id=account_id,
        role="admin",
        permissions=[],
        issued_at=int(datetime.now(timezone.utc).timestamp()) - 3600,
        expires_at=int(datetime.now(timezone.utc).timestamp()) - 10, # Expired
        token_id="expired_token_id"
    )
    
    expired_token_str = TokenCodec.encode(expired_payload, settings.token_secret)
    expired_headers = {"Authorization": f"Bearer {expired_token_str}"}
    
    expired_res = await client.get("/api/v1/auth/me", headers=expired_headers)
    assert expired_res.status_code == 401
