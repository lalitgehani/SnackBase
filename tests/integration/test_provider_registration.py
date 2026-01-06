"""Integration tests for provider registration during application startup."""

import pytest
from fastapi.testclient import TestClient

from snackbase.infrastructure.api.app import create_app


class TestProviderRegistration:
    """Test suite for provider registration on application startup."""

    @pytest.fixture
    def app(self):
        """Create a test application instance."""
        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_config_registry_exists_on_app_state(self, app):
        """Test that config_registry is created and stored on app.state."""
        # The lifespan context manager runs during TestClient initialization
        with TestClient(app):
            assert hasattr(app.state, "config_registry")
            assert app.state.config_registry is not None

    def test_email_password_provider_registered(self, app):
        """Test that email/password provider is registered on startup."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # Get the provider definition
            provider_def = config_registry.get_provider_definition(
                category="auth_providers",
                provider_name="email_password"
            )
            
            assert provider_def is not None
            assert provider_def.category == "auth_providers"
            assert provider_def.provider_name == "email_password"
            assert provider_def.display_name == "Email and Password"
            assert provider_def.is_builtin is True
            assert provider_def.config_schema == {}

    def test_google_oauth_provider_registered(self, app):
        """Test that Google OAuth provider is registered on startup."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # Get the provider definition
            provider_def = config_registry.get_provider_definition(
                category="auth_providers",
                provider_name="google"
            )
            
            assert provider_def is not None
            assert provider_def.category == "auth_providers"
            assert provider_def.provider_name == "google"
            assert provider_def.display_name == "Google"
            assert provider_def.is_builtin is True
            assert provider_def.logo_url == "/assets/providers/google.svg"
            assert "client_id" in provider_def.config_schema["properties"]
    def test_github_oauth_provider_registered(self, app):
        """Test that GitHub OAuth provider is registered on startup."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # Get the provider definition
            provider_def = config_registry.get_provider_definition(
                category="auth_providers",
                provider_name="github"
            )
            
            assert provider_def is not None
            assert provider_def.category == "auth_providers"
            assert provider_def.provider_name == "github"
            assert provider_def.display_name == "GitHub"
            assert provider_def.is_builtin is True
            assert provider_def.logo_url == "/assets/providers/github.svg"
            assert "client_id" in provider_def.config_schema["properties"]

    def test_microsoft_oauth_provider_registered(self, app):
        """Test that Microsoft OAuth provider is registered on startup."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # Get the provider definition
            provider_def = config_registry.get_provider_definition(
                category="auth_providers",
                provider_name="microsoft"
            )
            
            assert provider_def is not None
            assert provider_def.category == "auth_providers"
            assert provider_def.provider_name == "microsoft"
            assert provider_def.display_name == "Microsoft"
            assert provider_def.is_builtin is True
            assert provider_def.logo_url == "/assets/providers/microsoft.svg"
            assert "client_id" in provider_def.config_schema["properties"]
            assert "tenant_id" in provider_def.config_schema["properties"]

    def test_apple_oauth_provider_registered(self, app):
        """Test that Apple OAuth provider is registered on startup."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # Get the provider definition
            provider_def = config_registry.get_provider_definition(
                category="auth_providers",
                provider_name="apple"
            )
            
            assert provider_def is not None
            assert provider_def.category == "auth_providers"
            assert provider_def.provider_name == "apple"
            assert provider_def.display_name == "Apple"
            assert provider_def.is_builtin is True
            assert provider_def.logo_url == "/assets/providers/apple.svg"
            assert "client_id" in provider_def.config_schema["properties"]
            assert "team_id" in provider_def.config_schema["properties"]
            assert "key_id" in provider_def.config_schema["properties"]

    def test_provider_appears_in_list(self, app):
        """Test that provider appears in list of auth providers."""
        with TestClient(app):
            config_registry = app.state.config_registry
            
            # List all auth providers
            auth_providers = config_registry.list_provider_definitions(
                category="auth_providers"
            )
            
            # Find email_password provider
            email_password = next(
                (p for p in auth_providers if p.provider_name == "email_password"),
                None
            )
            
            assert email_password is not None
            assert email_password.is_builtin is True

    @pytest.mark.asyncio
    async def test_builtin_provider_cannot_be_deleted(self):
        """Test that attempting to delete a built-in provider raises ValueError."""
        # This test verifies the logic without needing the full app context
        from snackbase.core.configuration.config_registry import ConfigurationRegistry
        from snackbase.infrastructure.persistence.database import get_db_session
        from snackbase.infrastructure.persistence.repositories import (
            ConfigurationRepository,
            AccountRepository,
        )
        from snackbase.infrastructure.security.encryption import EncryptionService
        from snackbase.core.config import get_settings
        from snackbase.infrastructure.persistence.models import AccountModel
        
        settings = get_settings()
        
        async for session in get_db_session():
            try:
                # Ensure system account exists
                account_repo = AccountRepository(session)
                system_account = await account_repo.get_by_id("00000000-0000-0000-0000-000000000000")
                if not system_account:
                    # Create system account if it doesn't exist
                    system_account = AccountModel(
                        id="00000000-0000-0000-0000-000000000000",
                        account_code="SY0000",
                        account_name="System",
                    )
                    await account_repo.create(system_account)
                    await session.commit()
                
                config_repo = ConfigurationRepository(session)
                encryption_service = EncryptionService(settings.encryption_key)
                config_registry = ConfigurationRegistry(encryption_service)
                
                # Create a built-in configuration
                config = await config_registry.create_config(
                    account_id="00000000-0000-0000-0000-000000000000",
                    category="auth_providers",
                    provider_name="test_builtin",
                    display_name="Test Built-in",
                    config={},
                    is_builtin=True,
                    is_system=True,
                    repository=config_repo,
                )
                
                # Attempt to delete it - should raise ValueError
                with pytest.raises(ValueError, match="Built-in configurations cannot be deleted"):
                    await config_registry.delete_config(config.id, config_repo)
                
                # Clean up - delete directly from repository (bypassing the registry check)
                await config_repo.delete(config.id)
                await session.commit()
                break
            finally:
                await session.close()



