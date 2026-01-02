
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.configuration.providers.saml import (
    AzureADSAMLProvider,
    GenericSAMLProvider,
    OktaSAMLProvider,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    ConfigurationRepository,
)
from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.core.config import get_settings
from snackbase.core.configuration.config_registry import ConfigurationRegistry
from snackbase.infrastructure.security.encryption import EncryptionService

@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession):
    """Create a test account."""
    account = AccountModel(
        id="test-account-id",
        account_code="TA0001",
        name="Test Account",
        slug="test-account",
    )
    db_session.add(account)
    await db_session.commit()
    return account

@pytest.fixture
def auth_headers():
    """Mock auth headers."""
    return {"Authorization": "Bearer mock_token"}

@pytest_asyncio.fixture
async def setup_registry(client: AsyncClient, db_session: AsyncSession):
    """Ensure config_registry is initialized and attached to app state."""
    from snackbase.infrastructure.api.app import app
    
    settings = get_settings()
    config_repo = ConfigurationRepository(db_session)
    encryption_service = EncryptionService(settings.encryption_key)
    
    registry = ConfigurationRegistry(encryption_service)
    app.state.config_registry = registry
    
    # Register provider definitions
    okta_provider = OktaSAMLProvider()
    registry.register_provider_definition(
        category="saml_providers",
        name=okta_provider.provider_name,
        display_name=okta_provider.display_name,
        logo_url=okta_provider.logo_url,
        config_schema=okta_provider.config_schema,
        is_builtin=True,
    )
    
    azure_provider = AzureADSAMLProvider()
    registry.register_provider_definition(
        category="saml_providers",
        name=azure_provider.provider_name,
        display_name=azure_provider.display_name,
        logo_url=azure_provider.logo_url,
        config_schema=azure_provider.config_schema,
        is_builtin=True,
    )
    
    generic_provider = GenericSAMLProvider()
    registry.register_provider_definition(
        category="saml_providers",
        name=generic_provider.provider_name,
        display_name=generic_provider.display_name,
        logo_url=generic_provider.logo_url,
        config_schema=generic_provider.config_schema,
        is_builtin=True,
    )
    
    return registry


@pytest.mark.asyncio
async def test_saml_sso_initiate_success(
    client: AsyncClient,
    test_account,
    setup_registry,
    db_session: AsyncSession,
):
    """Test successful SAML SSO initiation."""
    registry = setup_registry
    
    # Enable Okta provider for this account
    okta_config = {
        "idp_entity_id": "http://www.okta.com/exk123456",
        "idp_sso_url": "https://dev-123456.okta.com/app/exk123456/sso/saml",
        "idp_x509_cert": "MIIDnDCCAoSgAwIBAgIG...",
        "sp_entity_id": "http://localhost:8000/api/v1/auth/saml/metadata",
        "assertion_consumer_url": "http://localhost:8000/api/v1/auth/saml/acs",
    }
    
    await registry.create_config(
        account_id=test_account.id,
        category="saml_providers",
        provider_name="okta",
        display_name="Okta SSO",
        config=okta_config,
        enabled=True,
        repository=ConfigurationRepository(db_session),
    )
    
    # Execute: Call the SSO endpoint
    response = await client.get(
        "/api/v1/auth/saml/sso",
        params={"account": test_account.slug},
        follow_redirects=False,
    )
    
    # Verify
    assert response.status_code == 302
    location = response.headers["location"]
    assert "https://dev-123456.okta.com/app/exk123456/sso/saml" in location
    assert "SAMLRequest=" in location

@pytest.mark.asyncio
async def test_saml_sso_specific_provider(
    client: AsyncClient,
    test_account,
    setup_registry,
    db_session: AsyncSession,
):
    """Test SAML SSO with specific provider requested."""
    registry = setup_registry
    
    # Enable Azure AD provider
    azure_config = {
        "idp_entity_id": "https://sts.windows.net/123/",
        "idp_sso_url": "https://login.microsoftonline.com/123/saml2",
        "idp_x509_cert": "MIIDnDCCAoSgAwIBAgIG...",
        "sp_entity_id": "http://localhost:8000",
        "assertion_consumer_url": "http://localhost:8000/acs",
    }
    
    await registry.create_config(
        account_id=test_account.id,
        category="saml_providers",
        provider_name="azure_ad",
        display_name="Azure AD",
        config=azure_config,
        enabled=True,
        repository=ConfigurationRepository(db_session),
    )
    
    response = await client.get(
        "/api/v1/auth/saml/sso",
        params={"account": test_account.slug, "provider": "azure_ad"},
        follow_redirects=False,
    )
    
    assert response.status_code == 302
    assert "login.microsoftonline.com" in response.headers["location"]

@pytest.mark.asyncio
async def test_saml_sso_relay_state(
    client: AsyncClient,
    test_account,
    setup_registry,
    db_session: AsyncSession,
):
    """Test SAML SSO preserves relay state."""
    registry = setup_registry
    
    # Use generic provider
    generic_config = {
        "idp_entity_id": "https://idp.example.com",
        "idp_sso_url": "https://idp.example.com/sso",
        "idp_x509_cert": "cert",
        "sp_entity_id": "sp",
        "assertion_consumer_url": "acs",
        "binding": "HTTP-Redirect",
    }
    
    await registry.create_config(
        account_id=test_account.id,
        category="saml_providers",
        provider_name="generic_saml",
        display_name="Generic",
        config=generic_config,
        enabled=True,
        repository=ConfigurationRepository(db_session),
    )
    
    relay_state = "return_to=/dashboard"
    response = await client.get(
        "/api/v1/auth/saml/sso",
        params={
            "account": test_account.slug, 
            "provider": "generic_saml",
            "relay_state": relay_state
        },
        follow_redirects=False,
    )
    
    assert response.status_code == 302
    # RelayState should be URL encoded in the location
    assert "RelayState=" in response.headers["location"]

@pytest.mark.asyncio
async def test_saml_sso_account_not_found(client: AsyncClient, setup_registry):
    """Test SSO with invalid account."""
    response = await client.get(
        "/api/v1/auth/saml/sso",
        params={"account": "non-existent-account-slug-12345"},
    )
    assert response.status_code == 404
    assert "Account" in response.json()["detail"]

@pytest.mark.asyncio
async def test_saml_sso_provider_not_configured(
    client: AsyncClient, 
    test_account,
    setup_registry,
):
    """Test SSO when no provider is configured."""
    # Ensure no configs exist for this account (fresh test account should have none)
    
    response = await client.get(
        "/api/v1/auth/saml/sso",
        params={"account": test_account.slug},
    )
    assert response.status_code == 404
    assert "No active SAML provider" in response.json()["detail"]
