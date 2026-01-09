
import pytest
from httpx import AsyncClient
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from snackbase.infrastructure.persistence.models import EmailVerificationTokenModel
import hashlib

@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient, db_session: AsyncSession):
    """Test full refresh token flow: Register -> Login -> Refresh -> Verify Rotation."""
    
    # 1. Register a user
    email = "refresh_flow@example.com"
    register_payload = {
        "email": email,
        "password": "Password123!",
        "account_name": "Refresh Flow Corp",
        "account_slug": "refresh-flow-corp"
    }
    
    res = await client.post("/api/v1/auth/register", json=register_payload)
    assert res.status_code == 201
    
    # 1.5. Verify email manually
    known_token = "refresh_test_token"
    known_hash = hashlib.sha256(known_token.encode()).hexdigest()
    
    await db_session.execute(
        update(EmailVerificationTokenModel)
        .where(EmailVerificationTokenModel.email == email)
        .values(token_hash=known_hash)
    )
    await db_session.commit()
    
    verify_res = await client.post("/api/v1/auth/verify-email", json={"token": known_token})
    assert verify_res.status_code == 200

    # 2. Login to get initial tokens
    login_payload = {
        "email": email,
        "password": "Password123!",
        "account": "refresh-flow-corp"
    }
    
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    initial_tokens = login_res.json()
    refresh_token_1 = initial_tokens["refresh_token"]
    access_token_1 = initial_tokens["token"]
    
    assert refresh_token_1 is not None
    
    # Wait to ensure iat changes (JWT uses seconds)
    await asyncio.sleep(2)
    
    # 3. Use refresh token to get new tokens
    refresh_payload = {"refresh_token": refresh_token_1}
    refresh_res = await client.post("/api/v1/auth/refresh", json=refresh_payload)
    
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    
    refresh_token_2 = new_tokens["refresh_token"]
    access_token_2 = new_tokens["token"]
    
    assert refresh_token_2 != refresh_token_1
    assert access_token_2 != access_token_1
    
    # 4. Verify old refresh token is invalid (Rotation)
    # Note: Depending on implementation, reused tokens might be just invalid or trigger security alerts
    reuse_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert reuse_res.status_code == 401
    
    # 5. Verify new refresh token works
    refresh_res_2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_2})
    assert refresh_res_2.status_code == 200

@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test refreshing with invalid token."""
    
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert refresh_res.status_code == 401

@pytest.mark.asyncio
async def test_access_token_as_refresh_token(client: AsyncClient, db_session: AsyncSession):
    """Test using an access token as a refresh token (should fail)."""
    
    # 1. Register
    email = "wrong_token_type@example.com"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "account_name": "Wrong Token Corp"
    })
    
    # 2. Verify
    known_token = "wrong_type_token"
    known_hash = hashlib.sha256(known_token.encode()).hexdigest()
    
    await db_session.execute(
        update(EmailVerificationTokenModel)
        .where(EmailVerificationTokenModel.email == email)
        .values(token_hash=known_hash)
    )
    await db_session.commit()
    
    await client.post("/api/v1/auth/verify-email", json={"token": known_token})
    
    # 3. Login to get tokens
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
        "account": "wrong-token-corp"
    }) # Note: slug is auto-generated from name if not provided (Wrong Token Corp -> wrong-token-corp)
    
    access_token = login_res.json()["token"]
    
    # 2. Try to refresh using access token
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert refresh_res.status_code == 401
