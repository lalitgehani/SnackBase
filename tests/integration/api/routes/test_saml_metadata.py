import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status

from snackbase.core.configuration.config_registry import ConfigurationRegistry
from snackbase.infrastructure.configuration.providers.saml.okta import OktaSAMLProvider

@pytest.mark.asyncio
async def test_get_metadata_success(client, db_session):
    """Test retrieving SAML metadata successfully."""
    # 1. Setup account and config
    from snackbase.infrastructure.persistence.models import AccountModel
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000001",
        account_code="AC0001",
        name="Test Account",
        slug="test-account"
    )
    db_session.add(account)
    await db_session.commit()

    # 2. Mock ConfigRegistry
    mock_registry = MagicMock(spec=ConfigurationRegistry)
    
    # Mock get_effective_config to return a valid Okta config
    mock_config = {
        "idp_entity_id": "http://www.okta.com/exk123456",
        "idp_sso_url": "https://dev-123456.okta.com/app/exk123456/sso/saml",
        "idp_x509_cert": "MIIDqDCCApCgAwIBAgIGAYxE...",
        "sp_entity_id": "http://localhost:8000/api/v1/auth/saml/metadata",
        "assertion_consumer_url": "http://localhost:8000/api/v1/auth/saml/acs",
    }
    mock_registry.get_effective_config = AsyncMock(return_value=mock_config)
    
    # Inject mock registry into app state
    client._transport.app.state.config_registry = mock_registry

    # 3. Call endpoint
    response = await client.get(
        "/api/v1/auth/saml/metadata",
        params={"account": "test-account", "provider": "okta"}
    )

    # 4. Verify response
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/xml"
    assert 'attachment; filename="saml-metadata.xml"' in response.headers["content-disposition"]
    
    content = response.text
    assert "EntityDescriptor" in content
    assert 'entityID="http://localhost:8000/api/v1/auth/saml/metadata"' in content
    assert "AssertionConsumerService" in content
    assert 'Location="http://localhost:8000/api/v1/auth/saml/acs"' in content


@pytest.mark.asyncio
async def test_get_metadata_account_not_found(client, db_session):
    """Test retrieving metadata for non-existent account."""
    mock_registry = MagicMock(spec=ConfigurationRegistry)
    client._transport.app.state.config_registry = mock_registry

    response = await client.get(
        "/api/v1/auth/saml/metadata",
        params={"account": "non-existent", "provider": "okta"}
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Account 'non-existent' not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_metadata_provider_not_configured(client, db_session):
    """Test retrieving metadata when provider is not configured."""
    # 1. Setup account
    from snackbase.infrastructure.persistence.models import AccountModel
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000001",
        account_code="AC0001",
        name="Test Account",
        slug="test-account"
    )
    db_session.add(account)
    await db_session.commit()

    # 2. Mock ConfigRegistry to return None
    mock_registry = MagicMock(spec=ConfigurationRegistry)
    mock_registry.get_effective_config = AsyncMock(return_value=None)
    client._transport.app.state.config_registry = mock_registry

    # 3. Call endpoint
    response = await client.get(
        "/api/v1/auth/saml/metadata",
        params={"account": "test-account", "provider": "okta"}
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "SAML provider 'okta' not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_metadata_auto_provider_selection(client, db_session):
    """Test retrieving metadata with automatic provider selection."""
    # 1. Setup account
    from snackbase.infrastructure.persistence.models import AccountModel
    account = AccountModel(
        id="00000000-0000-0000-0000-000000000001",
        account_code="AC0001",
        name="Test Account",
        slug="test-account"
    )
    db_session.add(account)
    await db_session.commit()

    # 2. Mock ConfigRegistry
    mock_registry = MagicMock(spec=ConfigurationRegistry)
    
    # Mock to return config for any SAML provider
    async def side_effect(category, account_id, provider_name, repository):
        return {
            "idp_entity_id": "https://sts.windows.net/...",
            "idp_sso_url": "https://login.microsoftonline.com/...",
            "idp_x509_cert": "MIID...",
            "sp_entity_id": "http://sp",
            "assertion_consumer_url": "http://acs",
        }

    mock_registry.get_effective_config = AsyncMock(side_effect=side_effect)
    client._transport.app.state.config_registry = mock_registry

    # 3. Call endpoint without specifying provider
    response = await client.get(
        "/api/v1/auth/saml/metadata",
        params={"account": "test-account"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert "EntityDescriptor" in response.text
