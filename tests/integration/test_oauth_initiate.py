import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    ConfigurationRepository,
    OAuthStateRepository,
)
from snackbase.core.config import get_settings

@pytest.mark.asyncio
class TestOAuthInitiate:
    """Integration tests for OAuth initiate endpoint."""

    async def _ensure_config_registry(self, db_session: AsyncSession):
        """Ensure config_registry is initialized and on app state."""
        from snackbase.infrastructure.api.app import app
        from snackbase.core.configuration.config_registry import ConfigurationRegistry
        from snackbase.infrastructure.security.encryption import EncryptionService
        from snackbase.infrastructure.configuration.providers.oauth import GoogleOAuthHandler
        
        if not hasattr(app.state, "config_registry"):
            settings = get_settings()
            config_repo = ConfigurationRepository(db_session)
            encryption_service = EncryptionService(settings.encryption_key)
            app.state.config_registry = ConfigurationRegistry(config_repo, encryption_service)
            
            # Register Google provider definition for tests
            google_handler = GoogleOAuthHandler()
            app.state.config_registry.register_provider_definition(
                category="auth_providers",
                name="google",
                display_name="Google",
                logo_url=google_handler.logo_url,
                config_schema=google_handler.config_schema,
                is_builtin=True
            )

    async def test_authorize_google_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful initiation of Google OAuth flow at system level."""
        await self._ensure_config_registry(db_session)
        
        # 1. Setup google config at system level
        config_repo = ConfigurationRepository(db_session)
        account_repo = AccountRepository(db_session)
        
        # System account should be created by conftest or migration
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
        from snackbase.infrastructure.api.app import app
        config_registry = app.state.config_registry
        
        test_config = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": ["openid", "email"],
            "redirect_uri": "http://localhost:8000/callback"
        }
        
        await config_registry.create_config(
            account_id="00000000-0000-0000-0000-000000000000",
            category="auth_providers",
            provider_name="google",
            display_name="Google",
            config=test_config,
            is_system=True,
            enabled=True
        )
        await db_session.commit()
        
        # 2. Call the API
        response = await client.post(
            "/api/v1/auth/oauth/google/authorize",
            json={
                "redirect_uri": "http://myapp.com/callback",
                "state": "test-state"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "google" in data["authorization_url"]
        assert "state=test-state" in data["authorization_url"]
        assert data["state"] == "test-state"
        assert data["provider"] == "google"
        
        # 3. Verify state is in database
        oauth_state_repo = OAuthStateRepository(db_session)
        state_record = await oauth_state_repo.get_by_token("test-state")
        assert state_record is not None
        assert state_record.provider_name == "google"
        assert state_record.redirect_uri == "http://myapp.com/callback"

    async def test_authorize_unconfigured_provider(self, client: AsyncClient, db_session: AsyncSession):
        """Test that unconfigured provider returns 404."""
        await self._ensure_config_registry(db_session)
        
        response = await client.post(
            "/api/v1/auth/oauth/nonexistent/authorize",
            json={
                "redirect_uri": "http://myapp.com/callback"
            }
        )
        assert response.status_code == 404
        assert "not configured" in response.json()["detail"]

    async def test_authorize_invalid_account(self, client: AsyncClient, db_session: AsyncSession):
        """Test that invalid account returns 404."""
        await self._ensure_config_registry(db_session)
        
        response = await client.post(
            "/api/v1/auth/oauth/google/authorize",
            json={
                "account": "NONEXISTENT",
                "redirect_uri": "http://myapp.com/callback"
            }
        )
        assert response.status_code == 404
        assert "Account 'NONEXISTENT' not found" in response.json()["detail"]

    async def test_authorize_auto_generated_state(self, client: AsyncClient, db_session: AsyncSession):
        """Test that state is auto-generated if not provided."""
        await self._ensure_config_registry(db_session)
        
        from snackbase.infrastructure.api.app import app
        config_registry = app.state.config_registry
        
        # Create google config for this test as well (db resets)
        await config_registry.create_config(
            account_id="00000000-0000-0000-0000-000000000000",
            category="auth_providers",
            provider_name="google",
            display_name="Google",
            config={"client_id": "test", "client_secret": "test", "scopes": [], "redirect_uri": "test"},
            is_system=True,
            enabled=True
        )
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/oauth/google/authorize",
            json={
                "redirect_uri": "http://myapp.com/callback"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] is not None
        assert len(data["state"]) > 10
        
        # Verify state is in database
        oauth_state_repo = OAuthStateRepository(db_session)
        state_record = await oauth_state_repo.get_by_token(data["state"])
        assert state_record is not None
