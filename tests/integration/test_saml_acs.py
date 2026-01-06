import pytest
import uuid
import base64
import json
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from snackbase.infrastructure.persistence.models import AccountModel, UserModel
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    ConfigurationRepository,
    UserRepository,
    RoleRepository,
)
from snackbase.core.config import get_settings

@pytest.mark.asyncio
class TestSAMLACS:
    """Integration tests for SAML ACS endpoint."""

    async def _setup_infra(self, db_session: AsyncSession):
        """Setup necessary infrastructure for SAML tests."""
        from snackbase.infrastructure.api.app import app
        from snackbase.core.configuration.config_registry import ConfigurationRegistry
        from snackbase.infrastructure.security.encryption import EncryptionService
        from snackbase.infrastructure.configuration.providers.saml import OktaSAMLProvider
        
        settings = get_settings()
        encryption_service = EncryptionService(settings.encryption_key)
        app.state.config_registry = ConfigurationRegistry(encryption_service)
        
        # Register Okta provider definition
        okta_handler = OktaSAMLProvider()
        app.state.config_registry.register_provider_definition(
            category="saml_providers",
            provider_name="okta",
            display_name="Okta",
            logo_url=okta_handler.logo_url,
            config_schema=okta_handler.config_schema,
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

        # Create system-level okta config
        test_config = {
            "idp_entity_id": "http://www.okta.com/exk123",
            "idp_sso_url": "https://dev-123.okta.com/app/exk123/sso/saml",
            "idp_x509_cert": "cert",
            "sp_entity_id": "http://localhost:8000/saml/metadata",
            "assertion_consumer_url": "http://localhost:8000/api/v1/auth/saml/acs"
        }
        
        await app.state.config_registry.create_config(
            account_id="00000000-0000-0000-0000-000000000000",
            category="saml_providers",
            provider_name="okta",
            display_name="Okta",
            config=test_config,
            is_system=True,
            enabled=True,
            repository=ConfigurationRepository(db_session)
        )
        await db_session.commit()

    async def test_acs_success_existing_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful ACS callback for an existing user."""
        await self._setup_infra(db_session)
        
        # Create an existing account and user
        account_repo = AccountRepository(db_session)
        role_repo = RoleRepository(db_session)
        user_repo = UserRepository(db_session)
        
        account = AccountModel(id=str(uuid.uuid4()), account_code="AC1234", name="Exist SAML Account", slug="saml-exist")
        await account_repo.create(account)
        
        admin_role = await role_repo.get_by_name("admin")
        user = UserModel(
            id=str(uuid.uuid4()),
            account_id=account.id,
            email="samluser@example.com",
            password_hash="hash",
            role_id=admin_role.id,
            auth_provider="saml",
            auth_provider_name="okta",
            external_id="okta-user-123",
            is_active=True
        )
        await user_repo.create(user)
        await db_session.commit()
        
        # Prepare RelayState
        relay_state_data = {
            "a": account.id,
            "p": "okta",
            "r": "some-original-state"
        }
        encoded_relay_state = base64.urlsafe_b64encode(json.dumps(relay_state_data).encode()).decode()
        
        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.parse_saml_response.return_value = {
            "id": "okta-user-123",
            "email": "samluser@example.com",
            "name": "SAML User"
        }
        
        with patch("snackbase.infrastructure.api.routes.saml_router.SAML_HANDLERS", {"okta": mock_handler}):
            response = await client.post(
                "/api/v1/auth/saml/acs",
                data={
                    "SAMLResponse": "dummy-base64-response",
                    "RelayState": encoded_relay_state
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "samluser@example.com"
        assert data["is_new_user"] is False
        assert data["account"]["id"] == account.id

    async def test_acs_success_new_user_provisioning(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful ACS callback creating a new user in an existing account."""
        await self._setup_infra(db_session)
        
        # Create an existing account
        account_repo = AccountRepository(db_session)
        account = AccountModel(id=str(uuid.uuid4()), account_code="AC9999", name="New User Account", slug="saml-new")
        await account_repo.create(account)
        await db_session.commit()
        
        # Prepare RelayState
        relay_state_data = {
            "a": account.id,
            "p": "okta",
            "r": None
        }
        encoded_relay_state = base64.urlsafe_b64encode(json.dumps(relay_state_data).encode()).decode()
        
        # Mock handler
        mock_handler = AsyncMock()
        mock_handler.parse_saml_response.return_value = {
            "id": "okta-new-user",
            "email": "new.saml@example.com",
            "name": "New SAML User"
        }
        
        with patch("snackbase.infrastructure.api.routes.saml_router.SAML_HANDLERS", {"okta": mock_handler}):
            response = await client.post(
                "/api/v1/auth/saml/acs",
                data={
                    "SAMLResponse": "dummy-response",
                    "RelayState": encoded_relay_state
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "new.saml@example.com"
        assert data["is_new_user"] is True
        assert data["account"]["id"] == account.id
        
        # Verify user in DB
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_external_id("okta", "okta-new-user")
        assert user is not None
        assert user.auth_provider == "saml"
        assert user.auth_provider_name == "okta"

    async def test_acs_missing_relay_state(self, client: AsyncClient, db_session: AsyncSession):
        """Test ACS fails without RelayState (context)."""
        response = await client.post(
            "/api/v1/auth/saml/acs",
            data={
                "SAMLResponse": "dummy"
            }
        )
        assert response.status_code == 400
        assert "Missing context" in response.json()["detail"]

    async def test_acs_invalid_relay_state(self, client: AsyncClient, db_session: AsyncSession):
        """Test ACS fails with invalid RelayState."""
        response = await client.post(
            "/api/v1/auth/saml/acs",
            data={
                "SAMLResponse": "dummy",
                "RelayState": "invalid-base64"
            }
        )
        assert response.status_code == 400
        assert "Missing context" in response.json()["detail"]

    async def test_acs_provider_not_configured(self, client: AsyncClient, db_session: AsyncSession):
        """Test ACS fails if provider not configured for account."""
        await self._setup_infra(db_session)
        
        # Use an account that doesn't exist or isn't configured, 
        # but account needs to exist for 'account not found' check?
        # Actually our code checks account exists first inside the loop? 
        # No, wait. In ACS:
        # 1. Decode context -> account_id, provider
        # 2. Get config. If no config -> 404 Provider not configured.
        
        # Let's use valid account ID but provider that isn't configured for it (and not system default)
        # But we set up system default okta. So 'okta' will work for any account.
        # Let's use 'azure_ad' which is not configured.
        
        relay_state_data = {
            "a": "00000000-0000-0000-0000-000000000000",
            "p": "azure_ad"
        }
        encoded_relay_state = base64.urlsafe_b64encode(json.dumps(relay_state_data).encode()).decode()
        
        response = await client.post(
            "/api/v1/auth/saml/acs",
            data={
                "SAMLResponse": "dummy",
                "RelayState": encoded_relay_state
            }
        )
        assert response.status_code == 404
        assert "Provider 'azure_ad' not configured" in response.json()["detail"]
