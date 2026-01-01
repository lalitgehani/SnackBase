
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


@pytest.mark.asyncio
async def test_oauth_user_cannot_login_with_password(client: AsyncClient, db_session: AsyncSession):
    """Test that OAuth users receive 400 error when attempting password login."""
    import uuid
    from snackbase.infrastructure.auth import hash_password
    from snackbase.infrastructure.persistence.models import AccountModel, RoleModel
    from snackbase.infrastructure.persistence.repositories import AccountRepository, RoleRepository
    
    # Create account
    account_repo = AccountRepository(db_session)
    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="OA0001",
        slug="oauth-test",
        name="OAuth Test Account",
    )
    await account_repo.create(account)
    
    # Get admin role
    role_repo = RoleRepository(db_session)
    admin_role = await role_repo.get_by_name("admin")
    
    # Create OAuth user
    user = UserModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        email="oauth@example.com",
        password_hash=hash_password("random_unknowable_password_12345"),
        role_id=admin_role.id,
        is_active=True,
        auth_provider="oauth",
        auth_provider_name="google",
        external_id="google_12345",
    )
    db_session.add(user)
    await db_session.commit()
    
    # Attempt login with password
    payload = {
        "email": "oauth@example.com",
        "password": "AnyPassword123!",
        "account": "oauth-test"
    }
    
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["error"] == "Wrong authentication method"
    assert "OAuth" in data["message"]
    assert data["auth_provider"] == "oauth"
    assert data["provider_name"] == "google"
    assert "/api/v1/auth/oauth/google/authorize" in data["redirect_url"]


@pytest.mark.asyncio
async def test_saml_user_cannot_login_with_password(client: AsyncClient, db_session: AsyncSession):
    """Test that SAML users receive 400 error when attempting password login."""
    import uuid
    from snackbase.infrastructure.auth import hash_password
    from snackbase.infrastructure.persistence.models import AccountModel, RoleModel
    from snackbase.infrastructure.persistence.repositories import AccountRepository, RoleRepository
    
    # Create account
    account_repo = AccountRepository(db_session)
    account = AccountModel(
        id=str(uuid.uuid4()),
        account_code="SA0001",
        slug="saml-test",
        name="SAML Test Account",
    )
    await account_repo.create(account)
    
    # Get admin role
    role_repo = RoleRepository(db_session)
    admin_role = await role_repo.get_by_name("admin")
    
    # Create SAML user
    user = UserModel(
        id=str(uuid.uuid4()),
        account_id=account.id,
        email="saml@example.com",
        password_hash=hash_password("random_unknowable_password_saml"),
        role_id=admin_role.id,
        is_active=True,
        auth_provider="saml",
        auth_provider_name="okta",
        external_id="okta_user_123",
    )
    db_session.add(user)
    await db_session.commit()
    
    # Attempt login with password
    payload = {
        "email": "saml@example.com",
        "password": "AnyPassword123!",
        "account": "saml-test"
    }
    
    res = await client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["error"] == "Wrong authentication method"
    assert "SAML" in data["message"]
    assert data["auth_provider"] == "saml"
    assert data["provider_name"] == "okta"
    assert "/api/v1/auth/saml/okta/login" in data["redirect_url"]
