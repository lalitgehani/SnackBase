
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models import UserModel

@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient, db_session: AsyncSession):
    """Test full login flow: Register -> Login -> Verify."""
    
    # 1. Register a user
    register_payload = {
        "email": "login_test@example.com",
        "password": "Password123!",
        "account_name": "Login Test Corp",
        "account_slug": "login-test-corp"
    }
    
    res = await client.post("/api/v1/auth/register", json=register_payload)
    assert res.status_code == 201
    account_id = res.json()["account"]["id"]
    
    # 2. Login with valid credentials
    login_payload = {
        "email": "login_test@example.com",
        "password": "Password123!",
        "account": "login-test-corp"
    }
    
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    data = login_res.json()
    
    # Verify response structure
    assert "token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "login_test@example.com"
    assert data["account"]["slug"] == "login-test-corp"
    assert data["account"]["id"] == account_id
    
    # 3. Verify last_login updated
    # We need a fresh session to see updates
    result = await db_session.execute(
        select(UserModel).where(UserModel.email == "login_test@example.com")
    )
    user = result.scalar_one()
    assert user.last_login is not None


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with incorrect password."""
    
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "wrong_pass@example.com",
        "password": "Password123!",
        "account_name": "Wrong Pass Corp"
    })
    
    payload = {
        "email": "wrong_pass@example.com",
        "password": "WrongPassword!",
        "account": "wrong-pass-corp"
    }
    
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_wrong_email(client: AsyncClient):
    """Test login with non-existent email."""
    
    # Register account but try different email
    await client.post("/api/v1/auth/register", json={
        "email": "real_email@example.com",
        "password": "Password123!",
        "account_name": "Wrong Email Corp",
        "account_slug": "wrong-email-corp"
    })
    
    payload = {
        "email": "fake_email@example.com",
        "password": "Password123!",
        "account": "wrong-email-corp"
    }
    
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_wrong_account(client: AsyncClient):
    """Test login with incorrect account."""
    
    # Register with one account
    await client.post("/api/v1/auth/register", json={
        "email": "multi_account@example.com",
        "password": "Password123!",
        "account_name": "Account A",
        "account_slug": "account-a"
    })
    
    # Try to login to different account (that might not even exist)
    payload = {
        "email": "multi_account@example.com",
        "password": "Password123!",
        "account": "account-b-nonexistent"
    }
    
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
    assert res.json()["message"] == "Invalid credentials"
