"""Unit tests for Azure AD SAML provider."""

import base64
import zlib
from unittest.mock import MagicMock, patch

import pytest
from lxml import etree

from snackbase.infrastructure.configuration.providers.saml.azure_ad import (
    AzureADSAMLProvider,
)


@pytest.fixture
def provider():
    """Create Azure AD SAML provider instance."""
    return AzureADSAMLProvider()


@pytest.fixture
def valid_config():
    """Create valid provider configuration."""
    return {
        "idp_entity_id": "https://sts.windows.net/azure-tenant-id/",
        "idp_sso_url": "https://login.microsoftonline.com/azure-tenant-id/saml2",
        "idp_x509_cert": "MIIDbtCCA... (mock cert)",
        "sp_entity_id": "snackbase-sp",
        "assertion_consumer_url": "https://api.snackbase.com/api/v1/auth/saml/acs",
    }


def test_provider_metadata(provider):
    """Test provider metadata properties."""
    assert provider.provider_name == "azure_ad"
    assert provider.display_name == "Azure AD"
    assert provider.logo_url == "/assets/providers/azure.svg"
    assert provider.provider_type == "saml"


def test_config_schema(provider):
    """Test configuration schema."""
    schema = provider.config_schema
    assert schema["type"] == "object"
    assert "idp_entity_id" in schema["required"]
    assert "idp_sso_url" in schema["required"]
    assert "idp_x509_cert" in schema["required"]
    assert "sp_entity_id" in schema["required"]
    assert "assertion_consumer_url" in schema["required"]


@pytest.mark.asyncio
async def test_get_authorization_url(provider, valid_config):
    """Test generating authorization URL."""
    url = await provider.get_authorization_url(
        valid_config,
        redirect_uri="https://api.snackbase.com/api/v1/auth/saml/acs",
        relay_state="return_to=/dashboard"
    )

    assert url.startswith(valid_config["idp_sso_url"])
    assert "SAMLRequest=" in url
    assert "RelayState=return_to%3D%2Fdashboard" in url

    # Extract SAMLRequest
    parsed_url = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed_url.query)
    saml_request_encoded = qs["SAMLRequest"][0]

    # Decode
    compressed = base64.b64decode(saml_request_encoded)
    xml_str = zlib.decompress(compressed, -15).decode("utf-8")  # Raw inflate

    # Verify XML content
    assert 'Destination="https://login.microsoftonline.com/azure-tenant-id/saml2"' in xml_str
    assert 'AssertionConsumerServiceURL="https://api.snackbase.com/api/v1/auth/saml/acs"' in xml_str
    assert 'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"' in xml_str
    assert '<saml:Issuer>snackbase-sp</saml:Issuer>' in xml_str


@pytest.mark.asyncio
async def test_parse_saml_response_success(provider, valid_config):
    """Test parsing a valid SAML response from Azure AD."""
    # Mock XMLVerifier to avoid actual signature verification logic
    # and return a constructed XML element representing a valid assertion
    
    mock_signed_xml = etree.fromstring("""
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">user@example.com</saml:NameID>
        </saml:Subject>
        <saml:AttributeStatement>
            <saml:Attribute Name="http://schemas.microsoft.com/identity/claims/objectidentifier">
                <saml:AttributeValue>oid-12345</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
                <saml:AttributeValue>user@example.com</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname">
                <saml:AttributeValue>John</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname">
                <saml:AttributeValue>Doe</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="http://schemas.microsoft.com/identity/claims/displayname">
                <saml:AttributeValue>John Doe</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
    """)

    with patch("snackbase.infrastructure.configuration.providers.saml.azure_ad.XMLVerifier") as MockVerifier:
        instance = MockVerifier.return_value
        instance.verify.return_value = MagicMock(signed_xml=mock_signed_xml)

        user_info = await provider.parse_saml_response(
            valid_config,
            saml_response="ZHVtbXk=" # "dummy"
        )

        assert user_info["id"] == "user@example.com"
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "John Doe"
        assert user_info["attributes"]["http://schemas.microsoft.com/identity/claims/objectidentifier"] == "oid-12345"


@pytest.mark.asyncio
async def test_parse_saml_response_fallback_name(provider, valid_config):
    """Test parsing SAML response using DisplayName claim."""
    mock_signed_xml = etree.fromstring("""
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        <saml:Subject>
            <saml:NameID>user@example.com</saml:NameID>
        </saml:Subject>
        <saml:AttributeStatement>
            <saml:Attribute Name="http://schemas.microsoft.com/identity/claims/displayname">
                <saml:AttributeValue>Jane Doe</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
    """)

    with patch("snackbase.infrastructure.configuration.providers.saml.azure_ad.XMLVerifier") as MockVerifier:
        instance = MockVerifier.return_value
        instance.verify.return_value = MagicMock(signed_xml=mock_signed_xml)

        user_info = await provider.parse_saml_response(
            valid_config,
            saml_response="ZHVtbXk="
        )

        assert user_info["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_parse_saml_response_upn_fallback(provider, valid_config):
    """Test parsing SAML response using UPN claim for email."""
    mock_signed_xml = etree.fromstring("""
    <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        <saml:Subject>
            <saml:NameID>oid-12345</saml:NameID>
        </saml:Subject>
        <saml:AttributeStatement>
            <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name">
                <saml:AttributeValue>user@example.com</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
    """)

    with patch("snackbase.infrastructure.configuration.providers.saml.azure_ad.XMLVerifier") as MockVerifier:
        instance = MockVerifier.return_value
        instance.verify.return_value = MagicMock(signed_xml=mock_signed_xml)

        user_info = await provider.parse_saml_response(
            valid_config,
            saml_response="ZHVtbXk="
        )
        
        # NameID used for ID
        assert user_info["id"] == "oid-12345"
        # UPN used for email
        assert user_info["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_metadata(provider, valid_config):
    """Test metadata generation."""
    metadata = await provider.get_metadata(valid_config)
    
    assert '<md:EntityDescriptor' in metadata
    assert f'entityID="{valid_config["sp_entity_id"]}"' in metadata
    assert f'Location="{valid_config["assertion_consumer_url"]}"' in metadata
    assert 'Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"' in metadata

import urllib.parse
