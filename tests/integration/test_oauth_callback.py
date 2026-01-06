import pytest
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from snackbase.infrastructure.persistence.models import AccountModel, UserModel
from snackbase.infrastructure.persistence.models.configuration import OAuthStateModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    ConfigurationRepository,
    OAuthStateRepository,
    UserRepository,
    RoleRepository,
)
from snackbase.core.config import get_settings

@pytest.mark.asyncio
class TestOAuthCallback:
    """Integration tests for OAuth callback endpoint."""

    async def _setup_infra(self, db_session: AsyncSession):
        """Setup necessary infrastructure for OAuth tests."""
        from snackbase.infrastructure.api.app import app
        from snackbase.core.configuration.config_registry import ConfigurationRegistry
        from snackbase.infrastructure.security.encryption import EncryptionService
        from snackbase.infrastructure.configuration.providers.oauth import GoogleOAuthHandler
        
        settings = get_settings()
        encryption_service = EncryptionService(settings.encryption_key)
        app.state.config_registry = ConfigurationRegistry(encryption_service)
        
        # Register Google provider definition
        google_handler = GoogleOAuthHandler()
        app.state.config_registry.register_provider_definition(
            category="auth_providers",
            provider_name="google",
            display_name="Google",
            logo_url=google_handler.logo_url,
            config_schema=google_handler.config_schema,
            is_builtin=True
        )

        # Create system account
        account_repo = AccountRepository(db_session)
        system_account = await account_repo.get_by_id("00000000-0000-0000-0000-000000000000")
        if not system_account:
            system_account = AccountModel(
                id="00000000-0000-0000-0000-000000000000",
                account_code="SY0000",
                name="System",
                slug="system"
            )
            db_session.add(system_account)
            await db_session.flush()

        # Create system-level google config
        test_config = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": ["openid", "email"],
            "redirect_uri": "http://localhost:8000/callback"
        }
        
        await app.state.config_registry.create_config(
            account_id="00000000-0000-0000-0000-000000000000",
            category="auth_providers",
            provider_name="google",
            display_name="Google",
            config=test_config,
            is_system=True,
            enabled=True,
            repository=ConfigurationRepository(db_session)
        )
        await db_session.commit()

    async def test_callback_new_user_self_provisioning_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful callback for a new user with self-provisioning (new account)."""
        await self._setup_infra(db_session)
        
        # 1. Create a valid state in the database
        state_token = "valid-state-token"
        oauth_state_repo = OAuthStateRepository(db_session)
        state_model = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=state_token,
            redirect_uri="http://myapp.com/callback",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            metadata_={"account_id": "00000000-0000-0000-0000-000000000000"}
        )
        await oauth_state_repo.create(state_model)
        await db_session.commit()

        # 2. Mock the OAuth handler
        mock_handler = AsyncMock()
        mock_handler.exchange_code_for_tokens.return_value = {"access_token": "mock-access-token"}
        mock_handler.get_user_info.return_value = {
            "id": "google-user-123",
            "email": "newuser@example.com",
            "name": "New User"
        }

        with patch("snackbase.infrastructure.api.routes.oauth_router.OAUTH_HANDLERS", {"google": mock_handler}):
            response = await client.post(
                "/api/v1/auth/oauth/google/callback",
                json={
                    "code": "auth-code",
                    "state": state_token,
                    "redirect_uri": "http://myapp.com/callback"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["is_new_user"] is True
        assert data["is_new_account"] is True
        
        # Verify user and account in DB
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_external_id("google", "google-user-123")
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.auth_provider == "oauth"
        assert user.auth_provider_name == "google"
        assert user.external_id == "google-user-123"
        
        # Verify state is deleted
        state = await oauth_state_repo.get_by_token(state_token)
        assert state is None

    async def test_callback_existing_user_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful callback for an existing OAuth user."""
        await self._setup_infra(db_session)
        
        # Create an existing account and user
        account_repo = AccountRepository(db_session)
        role_repo = RoleRepository(db_session)
        user_repo = UserRepository(db_session)
        
        account = AccountModel(id=str(uuid.uuid4()), account_code="AC1234", name="Exist Account", slug="exist")
        await account_repo.create(account)
        
        admin_role = await role_repo.get_by_name("admin")
        user = UserModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            email="existing@example.com",
            password_hash="hash",
            role_id=admin_role.id,
            auth_provider="oauth",
            auth_provider_name="google",
            external_id="google-user-456",
            is_active=True
        )
        await user_repo.create(user)
        await db_session.commit()
        
        # Create state
        state_token = "state-existing"
        oauth_state_repo = OAuthStateRepository(db_session)
        state_model = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=state_token,
            redirect_uri="http://myapp.com/callback",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            metadata_={"account_id": account.id}
        )
        await oauth_state_repo.create(state_model)
        await db_session.commit()
        
        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.exchange_code_for_tokens.return_value = {"access_token": "mock-token"}
        mock_handler.get_user_info.return_value = {
            "id": "google-user-456",
            "email": "existing@example.com",
            "name": "Existing User"
        }
        
        with patch("snackbase.infrastructure.api.routes.oauth_router.OAUTH_HANDLERS", {"google": mock_handler}):
            response = await client.post(
                "/api/v1/auth/oauth/google/callback",
                json={
                    "code": "code",
                    "state": state_token,
                    "redirect_uri": "http://myapp.com/callback"
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "existing@example.com"
        assert data["is_new_user"] is False
        assert data["is_new_account"] is False

    async def test_callback_invalid_state(self, client: AsyncClient, db_session: AsyncSession):
        """Test callback with invalid state token."""
        await self._setup_infra(db_session)
        
        response = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={
                "code": "code",
                "state": "invalid-state",
                "redirect_uri": "http://myapp.com/callback"
            }
        )
        assert response.status_code == 400
        assert "Invalid state token" in response.json()["detail"]

    async def test_callback_expired_state(self, client: AsyncClient, db_session: AsyncSession):
        """Test callback with expired state token."""
        await self._setup_infra(db_session)
        
        # Create expired state
        state_token = "expired-state"
        oauth_state_repo = OAuthStateRepository(db_session)
        state_model = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=state_token,
            redirect_uri="http://myapp.com/callback",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            metadata_={"account_id": "00000000-0000-0000-0000-000000000000"}
        )
        await oauth_state_repo.create(state_model)
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={
                "code": "code",
                "state": state_token,
                "redirect_uri": "http://myapp.com/callback"
            }
        )
        assert response.status_code == 400
        assert "State token expired" in response.json()["detail"]
        
        # Verify state is deleted
        state = await oauth_state_repo.get_by_token(state_token)
        assert state is None

    async def test_callback_join_existing_account_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful callback where user joins an existing specific account."""
        await self._setup_infra(db_session)
        
        # Create an existing account
        account_repo = AccountRepository(db_session)
        account = AccountModel(id=str(uuid.uuid4()), account_code="AC5678", name="Target Account", slug="target")
        await account_repo.create(account)
        await db_session.commit()
        
        # Create state targeting this account
        state_token = "state-join"
        oauth_state_repo = OAuthStateRepository(db_session)
        state_model = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=state_token,
            redirect_uri="http://myapp.com/callback",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            metadata_={"account_id": account.id}
        )
        await oauth_state_repo.create(state_model)
        await db_session.commit()
        
        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.exchange_code_for_tokens.return_value = {"access_token": "mock-token"}
        mock_handler.get_user_info.return_value = {
            "id": "google-user-join",
            "email": "join@example.com",
            "name": "Join User"
        }
        
        with patch("snackbase.infrastructure.api.routes.oauth_router.OAUTH_HANDLERS", {"google": mock_handler}):
            response = await client.post(
                "/api/v1/auth/oauth/google/callback",
                json={
                    "code": "code",
                    "state": state_token,
                    "redirect_uri": "http://myapp.com/callback"
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "join@example.com"
        assert data["account"]["id"] == account.id
        assert data["is_new_user"] is True
        assert data["is_new_account"] is False

    async def test_callback_inactive_user_error(self, client: AsyncClient, db_session: AsyncSession):
        """Test callback fails for an inactive user."""
        await self._setup_infra(db_session)
        
        # Create an inactive user
        account_repo = AccountRepository(db_session)
        role_repo = RoleRepository(db_session)
        user_repo = UserRepository(db_session)
        
        account = AccountModel(id=str(uuid.uuid4()), account_code="AC1111", name="Inactive Acc", slug="inactive")
        await account_repo.create(account)
        
        admin_role = await role_repo.get_by_name("admin")
        user = UserModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            email="inactive@example.com",
            password_hash="hash",
            role_id=admin_role.id,
            auth_provider="oauth",
            auth_provider_name="google",
            external_id="google-inactive",
            is_active=False
        )
        await user_repo.create(user)
        await db_session.commit()
        
        # Create state
        state_token = "state-inactive"
        oauth_state_repo = OAuthStateRepository(db_session)
        state_model = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider_name="google",
            state_token=state_token,
            redirect_uri="http://myapp.com/callback",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            metadata_={"account_id": account.id}
        )
        await oauth_state_repo.create(state_model)
        await db_session.commit()
        
        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.exchange_code_for_tokens.return_value = {"access_token": "mock-token"}
        mock_handler.get_user_info.return_value = {
            "id": "google-inactive",
            "email": "inactive@example.com",
            "name": "Inactive User"
        }
        
        with patch("snackbase.infrastructure.api.routes.oauth_router.OAUTH_HANDLERS", {"google": mock_handler}):
            response = await client.post(
                "/api/v1/auth/oauth/google/callback",
                json={
                    "code": "code",
                    "state": state_token,
                    "redirect_uri": "http://myapp.com/callback"
                }
            )
            
        assert response.status_code == 401
        assert "User account is inactive" in response.json()["detail"]
