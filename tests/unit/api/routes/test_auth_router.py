
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.api.app import app
from snackbase.infrastructure.api.routes.auth_router import router
from snackbase.infrastructure.api.schemas import RegisterRequest
from snackbase.domain.services import PasswordValidationError
from snackbase.domain.services import default_password_validator

# We need to override the get_db_session dependency to use a mock
# However, usually for unit tests of routers it's easier to mock the repository calls
# inside the route handler.

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_register_success(mock_session):
    """Test successful user registration."""
    # Mock data
    request_data = {
        "email": "test@example.com",
        "password": "Password123!",
        "account_name": "Test Company",
        "account_slug": "test-company"
    }

    # Mock dependencies
    with patch("snackbase.infrastructure.api.routes.auth_router.get_db_session", return_value=mock_session), \
         patch("snackbase.infrastructure.api.routes.auth_router.AccountRepository") as MockAccountRepo, \
         patch("snackbase.infrastructure.api.routes.auth_router.UserRepository") as MockUserRepo, \
         patch("snackbase.infrastructure.api.routes.auth_router.RoleRepository") as MockRoleRepo, \
         patch("snackbase.infrastructure.api.routes.auth_router.RefreshTokenRepository") as MockRefreshTokenRepo, \
         patch("snackbase.infrastructure.api.routes.auth_router.jwt_service") as mock_jwt_service, \
         patch("snackbase.infrastructure.api.routes.auth_router.hash_password") as mock_hash:

        # Setup mocks
        mock_account_repo = MockAccountRepo.return_value
        mock_account_repo.slug_exists.return_value = False
        mock_account_repo.get_all_ids.return_value = []
        
        mock_user_repo = MockUserRepo.return_value
        
        mock_role_repo = MockRoleRepo.return_value
        mock_role = MagicMock()
        mock_role.id = "role_id"
        mock_role.name = "admin"
        mock_role_repo.get_by_name.return_value = mock_role
        
        mock_jwt_service.create_access_token.return_value = "access_token"
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token", "token_id")
        mock_jwt_service.get_expires_in.return_value = 3600
        
        # Test call - using TestClient would require overriding dependency at app level
        # For unit testing the router function directly is often cleaner if we don't want to setup full app context
        # But here we are testing the route integration with dependencies mocked. 
        # Let's use the router directly or TestClient with dependency overrides.
        pass

# Actually, for unit testing routes where we mock everything inside, 
# it's often better to test the function directly or use dependency_overrides.
# Let's try testing the route path via TestClient but we need to patch objects 
# where they are imported in auth_router.

@patch("snackbase.infrastructure.api.routes.auth_router.default_password_validator")
@patch("snackbase.infrastructure.api.routes.auth_router.SlugGenerator")
@patch("snackbase.infrastructure.api.routes.auth_router.AccountRepository")
@patch("snackbase.infrastructure.api.routes.auth_router.UserRepository")
@patch("snackbase.infrastructure.api.routes.auth_router.RoleRepository")
@patch("snackbase.infrastructure.api.routes.auth_router.RefreshTokenRepository")
@patch("snackbase.infrastructure.api.routes.auth_router.jwt_service")
@patch("snackbase.infrastructure.api.routes.auth_router.hash_password")
@patch("snackbase.infrastructure.api.routes.auth_router.AccountIdGenerator")
def test_register_endpoint_success(
    mock_id_gen,
    mock_hash,
    mock_jwt,
    mock_refresh_repo,
    mock_role_repo,
    mock_user_repo,
    mock_account_repo,
    mock_slug_gen,
    mock_password_validator,
    client
):
    """Test successful registration flow via API client."""
    
    # Configure Mocks
    mock_password_validator.validate.return_value = [] # No errors
    mock_slug_gen.validate.return_value = [] # No errors
    
    account_repo_instance = mock_account_repo.return_value
    account_repo_instance.slug_exists = AsyncMock(return_value=False)
    account_repo_instance.get_all_ids = AsyncMock(return_value=[])
    account_repo_instance.create = AsyncMock()
    
    role_repo_instance = mock_role_repo.return_value
    role_mock = MagicMock()
    role_mock.id = "admin-role-id"
    role_mock.name = "admin"
    role_repo_instance.get_by_name = AsyncMock(return_value=role_mock)
    
    user_repo_instance = mock_user_repo.return_value
    user_repo_instance.create = AsyncMock()
    
    refresh_repo_instance = mock_refresh_repo.return_value
    refresh_repo_instance.hash_token.return_value = "hashed_token"
    refresh_repo_instance.create = AsyncMock()
    
    mock_hash.return_value = "hashed_password"
    mock_id_gen.generate.return_value = "XY1234"
    
    mock_jwt.create_access_token.return_value = "fake_access_token"
    mock_jwt.create_refresh_token.return_value = ("fake_refresh_token", "fake_token_id")
    mock_jwt.get_expires_in.return_value = 3600
    
    # Mock session refresh to set created_at
    from datetime import datetime
    
    async def mock_refresh(instance):
        instance.created_at = datetime.now()
        instance.updated_at = datetime.now()

    # We need to override the database dependency to return a mock session
    # effectively ignoring the real DB connection
    session_mock = AsyncMock()
    session_mock.refresh = AsyncMock(side_effect=mock_refresh)
    
    async def override_get_db_session():
        yield session_mock
        
    from snackbase.infrastructure.persistence.database import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    payload = {
        "email": "test@example.com",
        "password": "Password123!",
        "account_name": "Test Account",
        "account_slug": "test-account"
    }
    
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["token"] == "fake_access_token"
    assert data["refresh_token"] == "fake_refresh_token"
    assert data["account"]["slug"] == "test-account"
    assert data["user"]["email"] == "test@example.com"
    
    # Verify mocks called
    account_repo_instance.slug_exists.assert_called_with("test-account")
    user_repo_instance.create.assert_called_once()
    
    # Cleanup
    app.dependency_overrides = {}


@patch("snackbase.infrastructure.api.routes.auth_router.default_password_validator")
def test_register_password_validation_error(mock_validator, client):
    """Test registration fails with weak password."""
    
    mock_error = PasswordValidationError(
        message="Password too short",
        code="password_too_short",
        field="password"
    )
    mock_validator.validate.return_value = [mock_error]
    
    payload = {
        "email": "test@example.com",
        "password": "weak",
        "account_name": "Test Account"
    }
    
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Validation error"
    assert data["details"][0]["code"] == "password_too_short"


@patch("snackbase.infrastructure.api.routes.auth_router.default_password_validator")
@patch("snackbase.infrastructure.api.routes.auth_router.AccountRepository")
def test_register_slug_conflict(mock_account_repo, mock_validator, client):
    """Test registration fails when slug already exists."""
    
    mock_validator.validate.return_value = []
    
    repo_instance = mock_account_repo.return_value
    repo_instance.slug_exists = AsyncMock(return_value=True)
    
    # Override DB session
    from snackbase.infrastructure.persistence.database import get_db_session
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    
    payload = {
        "email": "test@example.com",
        "password": "Password123!",
        "account_name": "Test Account",
        "account_slug": "existing-slug"
    }
    
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 409
    data = response.json()
    assert data["field"] == "account_slug"
    
    # Cleanup
    app.dependency_overrides = {}

