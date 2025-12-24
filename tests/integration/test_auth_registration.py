
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
import pytest_asyncio
from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.persistence.models.role import RoleModel

@pytest_asyncio.fixture
async def seed_roles(db_session):
    """Seed default roles."""
    roles = [
        RoleModel(name="admin", description="Administrator"),
        RoleModel(name="user", description="Normal user"),
    ]
    db_session.add_all(roles)
    await db_session.commit()

@pytest.mark.asyncio
async def test_register_integration_success(db_session, seed_roles):
    """Test full registration flow with in-memory database."""
    
    # We need to use the app with the database session overridden or 
    # configured to use the test database.
    # The 'db_session' fixture creates a session connected to in-memory DB.
    # We need to make sure the app uses this session.
    
    # Define override
    async def override_get_db_session():
        yield db_session

    from snackbase.infrastructure.persistence.database import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    payload = {
        "email": "integration@example.com",
        "password": "StrongPassword123!",
        "account_name": "Integration Corp"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    assert "token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "integration@example.com"
    assert data["account"]["name"] == "Integration Corp"
    assert "slug" in data["account"]
    
    # Verify in DB
    result = await db_session.execute(
        text("SELECT * FROM accounts WHERE id = :id"), 
        {"id": data["account"]["id"]}
    )
    account_row = result.mappings().one()
    assert account_row["name"] == "Integration Corp"
    
    result = await db_session.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": "integration@example.com"}
    )
    user_row = result.mappings().one()
    assert user_row["account_id"] == data["account"]["id"]
    
    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_register_integration_duplicate_slug(db_session, seed_roles):
    """Test registration with existing slug."""
    
    async def override_get_db_session():
        yield db_session
        
    from snackbase.infrastructure.persistence.database import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    # 1. Create first account
    payload1 = {
        "email": "user1@example.com",
        "password": "StrongPassword123!",
        "account_name": "Unique Company",
        "account_slug": "unique-co"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json=payload1)
        
    # 2. Try to create second account with same slug
    payload2 = {
        "email": "user2@example.com",
        "password": "StrongPassword123!",
        "account_name": "Copycat Corp",
        "account_slug": "unique-co"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/register", json=payload2)
        
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "Conflict"
    
    # Cleanup
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_register_integration_invalid_password(db_session):
    """Test registration with invalid password."""
    
    # Even for validation errors that don't hit DB, we might want to ensure
    # integration is correct (e.g. middleware, error handlers)
    
    payload = {
        "email": "weak@example.com",
        "password": "weak",
        "account_name": "Weak Corp"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/register", json=payload)
        
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Validation error"

