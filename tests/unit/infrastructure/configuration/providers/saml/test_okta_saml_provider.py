"""Unit tests for OktaSAMLProvider."""

import base64
import zlib
from unittest.mock import MagicMock, patch

import pytest
from lxml import etree

from snackbase.infrastructure.configuration.providers.saml.okta import OktaSAMLProvider


class TestOktaSAMLProvider:
    """Test suite for OktaSAMLProvider."""

    @pytest.fixture
    def provider(self):
        return OktaSAMLProvider()

    @pytest.fixture
    def valid_config(self):
        return {
            "idp_entity_id": "http://www.okta.com/exk123",
            "idp_sso_url": "https://dev-123.okta.com/app/exk123/sso/saml",
            "idp_x509_cert": "MIIDnDCCAoSgAwIBAgIG...",
            "sp_entity_id": "https://api.snackbase.com/api/v1/auth/saml/metadata",
            "assertion_consumer_url": "https://api.snackbase.com/api/v1/auth/saml/acs",
        }

    def test_provider_metadata(self, provider):
        """Test provider metadata properties."""
        assert provider.provider_name == "okta"
        assert provider.display_name == "Okta"
        assert provider.logo_url == "/assets/providers/okta.svg"
        assert provider.provider_type == "saml"

    def test_config_schema(self, provider):
        """Test configuration schema."""
        schema = provider.config_schema
        assert "idp_entity_id" in schema["required"]
        assert "idp_sso_url" in schema["required"]
        assert "idp_x509_cert" in schema["required"]
        assert "sp_entity_id" in schema["required"]
        assert "assertion_consumer_url" in schema["required"]

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, provider, valid_config):
        """Test generation of SAML AuthnRequest URL."""
        url = await provider.get_authorization_url(valid_config, "http://localhost/callback")

        # Check basic URL structure
        assert url.startswith(valid_config["idp_sso_url"])
        assert "SAMLRequest=" in url

        # Extract and decode SAMLRequest
        parsed =  dict(part.split("=") for part in url.split("?")[1].split("&"))
        encoded_req = parsed["SAMLRequest"]
        # URL decode is handled by parsing, but here we manually did split.
        # urllib.parse.urlencode encodes value, so we need to decode.
        import urllib.parse
        encoded_req = urllib.parse.unquote(encoded_req)
        
        # Base64 decode and Inflate
        compressed = base64.b64decode(encoded_req)
        # We need to handle raw deflate (no header) - which zlib.decompress usually needs wbits=-15
        xml_bytes = zlib.decompress(compressed, -15)
        xml_str = xml_bytes.decode("utf-8")

        # Verify XML content
        assert 'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"' in xml_str
        assert f'Destination="{valid_config["idp_sso_url"]}"' in xml_str
        assert f'AssertionConsumerServiceURL="{valid_config["assertion_consumer_url"]}"' in xml_str
        assert f'<saml:Issuer>{valid_config["sp_entity_id"]}</saml:Issuer>' in xml_str

    @pytest.mark.asyncio
    async def test_get_authorization_url_with_relay_state(self, provider, valid_config):
        """Test generation of SAML AuthnRequest URL with RelayState."""
        relay_state = "abc-123"
        url = await provider.get_authorization_url(valid_config, "http://cb", relay_state)
        
        assert f"RelayState={relay_state}" in url

    @pytest.mark.asyncio
    @patch("snackbase.infrastructure.configuration.providers.saml.okta.XMLVerifier")
    async def test_parse_saml_response_valid(self, mock_verifier_cls, provider, valid_config):
        """Test parsing a valid SAML response."""
        # Mock XMLVerifier instance and verify method
        mock_verifier = MagicMock()
        mock_verifier_cls.return_value = mock_verifier
        
        # Create a mock verified XML structure
        ns_saml = "urn:oasis:names:tc:SAML:2.0:assertion"
        ns_map = {"saml": ns_saml}
        
        assertion = etree.Element(f"{{{ns_saml}}}Assertion", nsmap=ns_map)
        
        subject = etree.SubElement(assertion, f"{{{ns_saml}}}Subject")
        name_id = etree.SubElement(subject, f"{{{ns_saml}}}NameID")
        name_id.text = "user@example.com"
        
        attr_stmt = etree.SubElement(assertion, f"{{{ns_saml}}}AttributeStatement")
        
        # FirstName
        attr_fn = etree.SubElement(attr_stmt, f"{{{ns_saml}}}Attribute", Name="firstName")
        val_fn = etree.SubElement(attr_fn, f"{{{ns_saml}}}AttributeValue")
        val_fn.text = "John"
        
        # LastName
        attr_ln = etree.SubElement(attr_stmt, f"{{{ns_saml}}}Attribute", Name="lastName")
        val_ln = etree.SubElement(attr_ln, f"{{{ns_saml}}}AttributeValue")
        val_ln.text = "Doe"
        
        mock_verifier.verify.return_value.signed_xml = assertion

        # Call method
        saml_response_b64 = base64.b64encode(b"<dummy>SAML</dummy>").decode("utf-8")
        user_info = await provider.parse_saml_response(valid_config, saml_response_b64)

        # Assertions
        assert user_info["id"] == "user@example.com"
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "John Doe"
        assert user_info["attributes"]["firstName"] == "John"

    @pytest.mark.asyncio
    @patch("snackbase.infrastructure.configuration.providers.saml.okta.XMLVerifier")
    async def test_parse_saml_response_invalid_signature(self, mock_verifier_cls, provider, valid_config):
        """Test parsing with invalid signature raises error."""
        mock_verifier = MagicMock()
        mock_verifier_cls.return_value = mock_verifier
        
        # Simulate verification failure
        from signxml import InvalidSignature
        mock_verifier.verify.side_effect = InvalidSignature("Signature invalid")

        with pytest.raises(ValueError, match="SAML validation failed"):
            await provider.parse_saml_response(valid_config, "base64data")

    @pytest.mark.asyncio
    async def test_get_metadata(self, provider, valid_config):
        """Test SP metadata generation."""
        metadata = await provider.get_metadata(valid_config)
        
        assert '<md:EntityDescriptor' in metadata
        assert f'entityID="{valid_config["sp_entity_id"]}"' in metadata
        assert f'Location="{valid_config["assertion_consumer_url"]}"' in metadata

    @pytest.mark.asyncio
    async def test_test_connection_calls_get_metadata(self, provider, valid_config):
        """Test that test_connection calls get_metadata and returns True."""
        # Fix: Mock needs to be an async mock or return a future
        with patch.object(provider, 'get_metadata', new_callable=MagicMock) as mock_meta:
            # Configure mock to be awaitable
            async def async_mock(*args, **kwargs):
                return "<xml>metadata</xml>"
            mock_meta.side_effect = async_mock

            result, message = await provider.test_connection(valid_config)
            assert result is True
            assert "Metadata generated successfully" in message
            mock_meta.assert_called_once_with(valid_config)
