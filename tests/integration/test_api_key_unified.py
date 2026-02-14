
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import hashlib

from snackbase.infrastructure.persistence.models import UserModel, EmailVerificationTokenModel
from snackbase.infrastructure.auth.api_key_service import api_key_service

@pytest.mark.asyncio
async def test_api_key_unified(client: AsyncClient, db_session: AsyncSession):
    """Test the unified API key flow."""
    
    # 1. Setup: Register and Verify User
    register_payload = {
        "email": "apikey_unified@example.com",
        "password": "Password123!",
        "account_name": "API Key Corp",
        "account_slug": "apikey-corp"
    }
    
    res = await client.post("/api/v1/auth/register", json=register_payload)
    assert res.status_code == 201
    account_id = res.json()["account"]["id"]
    
    # Verify email manually
    known_token = "test_verification_token_apikey"
    known_hash = hashlib.sha256(known_token.encode()).hexdigest()
    
    await db_session.execute(
        update(EmailVerificationTokenModel)
        .where(EmailVerificationTokenModel.email == "apikey_unified@example.com")
        .values(token_hash=known_hash)
    )
    await db_session.commit()
    
    verify_res = await client.post("/api/v1/auth/verify-email", json={"token": known_token})
    assert verify_res.status_code == 200

    # Get User ID
    user = (await db_session.execute(select(UserModel).where(UserModel.email == "apikey_unified@example.com"))).scalar_one()
    
    # 2. Test API Key Creation
    api_key, key_model = await api_key_service.create_api_key(
        session=db_session,
        user_id=user.id,
        email=user.email,
        account_id=user.account_id,
        role="admin",
        name="Test API Key",
        permissions=[]
    )
    await db_session.commit()
    
    assert api_key.startswith("sb_ak.")
    assert key_model.id is not None
    
    # 3. Test Access with API Key
    headers = {"X-API-Key": api_key}
    
    # Use /api/v1/auth/me to verify identity
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "apikey_unified@example.com"
    assert user_data["user_id"] == user.id
    
    # 4. Test API Key Revocation
    await api_key_service.revoke_api_key(
        token_id=key_model.id,
        session=db_session,
        reason="Test revocation"
    )
    await db_session.commit()
    
    # Try access again - should fail
    # Note: Authenticator checks blacklist for sb_ tokens
    revoked_res = await client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
