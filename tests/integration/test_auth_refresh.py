
import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
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
async def test_access_token_as_refresh_token(client: AsyncClient):
    """Test using an access token as a refresh token (should fail)."""
    
    # 1. Register & Login
    res = await client.post("/api/v1/auth/register", json={
        "email": "wrong_token_type@example.com",
        "password": "Password123!",
        "account_name": "Wrong Token Corp"
    })
    access_token = res.json()["token"]
    
    # 2. Try to refresh using access token
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert refresh_res.status_code == 401
