"""Unit tests for Generic SAML provider."""

import base64
import zlib
from unittest.mock import Mock, patch

import pytest
from lxml import etree
from signxml import XMLVerifier

from snackbase.infrastructure.configuration.providers.saml.generic import (
    GenericSAMLProvider,
)


@pytest.fixture
def provider():
    """Create a GenericSAMLProvider instance."""
    return GenericSAMLProvider()


@pytest.fixture
def valid_config():
    """Create a valid provider configuration."""
    return {
        "idp_entity_id": "http://idp.example.com",
        "idp_sso_url": "http://idp.example.com/sso",
        "idp_x509_cert": "-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----",
        "sp_entity_id": "http://sp.example.com",
        "assertion_consumer_url": "http://sp.example.com/acs",
        "binding": "HTTP-Redirect",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    }


def test_provider_properties(provider):
    """Test provider metadata properties."""
    assert provider.provider_name == "generic_saml"
    assert provider.display_name == "SAML 2.0"
    assert provider.logo_url == "/assets/providers/saml.svg"
    assert provider.provider_type == "saml"


def test_config_schema(provider):
    """Test configuration schema."""
    schema = provider.config_schema
    assert "idp_entity_id" in schema["required"]
    assert "binding" in schema["properties"]
    assert schema["properties"]["binding"]["enum"] == ["HTTP-Redirect", "HTTP-POST"]


@pytest.mark.asyncio
async def test_get_authorization_url(provider, valid_config):
    """Test generation of authorization URL."""
    url = await provider.get_authorization_url(
        config=valid_config,
        redirect_uri="http://sp.example.com/acs",
        relay_state="state123",
    )

    assert url.startswith("http://idp.example.com/sso?")
    assert "SAMLRequest=" in url
    assert "RelayState=state123" in url
    
    # Check separator logic
    config_with_query = valid_config.copy()
    config_with_query["idp_sso_url"] = "http://idp.example.com/sso?id=1"
    url2 = await provider.get_authorization_url(
        config=config_with_query,
        redirect_uri="http://sp.example.com/acs",
    )
    assert "&SAMLRequest=" in url2


@pytest.mark.asyncio
async def test_parse_saml_response_valid(provider, valid_config):
    """Test parsing a valid SAML response."""
    # Mock XMLVerifier to avoid needing real cert/signature
    mock_verifier = Mock(spec=XMLVerifier)
    mock_signed_xml = Mock()
    
    # Create a mock XML structure for the assertion
    ns = {
        'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
    }
    
    # Mock find/findall behavior
    def mock_find(path, namespaces=None):
        if path == ".//saml:NameID":
            mock_name_id = Mock()
            mock_name_id.text = "user@example.com"
            return mock_name_id
        return None
        
    def mock_findall(path, namespaces=None):
        if path == ".//saml:AttributeStatement/saml:Attribute":
            # Create attribute mocks
            attr1 = Mock()
            attr1.get.return_value = "firstName"
            val1 = Mock()
            val1.text = "John"
            attr1.findall.return_value = [val1]
            
            attr2 = Mock()
            attr2.get.return_value = "lastName"
            val2 = Mock()
            val2.text = "Doe"
            attr2.findall.return_value = [val2]
            
            return [attr1, attr2]
        return []

    mock_signed_xml.find.side_effect = mock_find
    mock_signed_xml.findall.side_effect = mock_findall
    
    mock_verifier.verify.return_value.signed_xml = mock_signed_xml

    with patch("snackbase.infrastructure.configuration.providers.saml.generic.XMLVerifier", return_value=mock_verifier):
        # Input doesn't matter much as we mock verify
        saml_response = base64.b64encode(b"<xml>dummy</xml>").decode("utf-8")
        
        user_info = await provider.parse_saml_response(valid_config, saml_response)
        
        assert user_info["id"] == "user@example.com"
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "John Doe"
        assert user_info["attributes"]["firstName"] == "John"
        assert user_info["attributes"]["lastName"] == "Doe"


@pytest.mark.asyncio
async def test_parse_saml_response_fallback_attributes(provider, valid_config):
    """Test parsing logic for email/name fallback."""
    mock_verifier = Mock(spec=XMLVerifier)
    mock_signed_xml = Mock()
    
    def mock_find(path, namespaces=None):
        if path == ".//saml:NameID":
            mock_name_id = Mock()
            mock_name_id.text = "random_id_123" # Not an email
            return mock_name_id
        return None

    def mock_findall(path, namespaces=None):
        if path == ".//saml:AttributeStatement/saml:Attribute":
            # Email attribute
            attr1 = Mock()
            attr1.get.return_value = "mail"
            val1 = Mock()
            val1.text = "real@example.com"
            attr1.findall.return_value = [val1]
            
            # Display name 
            attr2 = Mock()
            attr2.get.return_value = "displayName"
            val2 = Mock()
            val2.text = "Admin User"
            attr2.findall.return_value = [val2]
            
            return [attr1, attr2]
        return []

    mock_signed_xml.find.side_effect = mock_find
    mock_signed_xml.findall.side_effect = mock_findall
    mock_verifier.verify.return_value.signed_xml = mock_signed_xml

    with patch("snackbase.infrastructure.configuration.providers.saml.generic.XMLVerifier", return_value=mock_verifier):
        user_info = await provider.parse_saml_response(valid_config, "b64dummy")
        
        assert user_info["id"] == "random_id_123"
        assert user_info["email"] == "real@example.com"
        assert user_info["name"] == "Admin User"


@pytest.mark.asyncio
async def test_get_metadata(provider, valid_config):
    """Test SP metadata generation."""
    metadata = await provider.get_metadata(valid_config)
    
    assert 'entityID="http://sp.example.com"' in metadata
    assert 'Location="http://sp.example.com/acs"' in metadata
    assert '<md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>' in metadata
