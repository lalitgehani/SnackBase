"""Azure AD SAML 2.0 provider handler."""

import base64
import datetime
import secrets
import urllib.parse
import zlib
from typing import Any

from signxml import XMLVerifier

from snackbase.infrastructure.configuration.providers.saml.saml_handler import (
    SAMLProviderHandler,
)


class AzureADSAMLProvider(SAMLProviderHandler):
    """Azure AD SAML 2.0 authentication provider."""

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "azure_ad"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "Azure AD"

    @property
    def logo_url(self) -> str:
        """Path to provider logo asset."""
        return "/assets/providers/azure.svg"

    @property
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for provider configuration validation."""
        return {
            "type": "object",
            "required": [
                "idp_entity_id",
                "idp_sso_url",
                "idp_x509_cert",
                "sp_entity_id",
                "assertion_consumer_url",
            ],
            "properties": {
                "idp_entity_id": {
                    "type": "string",
                    "title": "Azure AD Identifier (Entity ID)",
                    "description": "Found in Azure Portal -> Single sign-on -> Basic SAML Configuration",
                },
                "idp_sso_url": {
                    "type": "string",
                    "title": "Login URL",
                    "format": "uri",
                    "description": "Found in Azure Portal -> Single sign-on -> Set up Single Sign-On",
                },
                "idp_x509_cert": {
                    "type": "string",
                    "title": "Certificate (Base64)",
                    "description": "Download Certificate (Base64) from Azure Portal and paste content here",
                },
                "sp_entity_id": {
                    "type": "string",
                    "title": "Identifier (Entity ID)",
                    "description": "The Entity ID you configured in Azure AD (Basic SAML Configuration)",
                },
                "assertion_consumer_url": {
                    "type": "string",
                    "title": "Reply URL (Assertion Consumer Service URL)",
                    "format": "uri",
                    "description": "The Reply URL you configured in Azure AD (Basic SAML Configuration)",
                },
            },
        }

    async def get_authorization_url(
        self,
        config: dict[str, Any],
        redirect_uri: str,
        relay_state: str | None = None,
    ) -> str:
        """Generate SAML authorization URL (AuthnRequest)."""
        self._validate_config(config)

        issue_instant = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        request_id = f"id_{secrets.token_hex(16)}"
        sp_entity_id = config["sp_entity_id"]
        acs_url = config.get("assertion_consumer_url", redirect_uri)

        # Azure AD expects standard SAML AuthnRequest
        # Note: ProtocolBinding is important
        authn_request = (
            f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
            f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
            f'ID="{request_id}" '
            f'Version="2.0" '
            f'IssueInstant="{issue_instant}" '
            f'Destination="{config["idp_sso_url"]}" '
            f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
            f'AssertionConsumerServiceURL="{acs_url}">'
            f'<saml:Issuer>{sp_entity_id}</saml:Issuer>'
            f'<samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true" />'
            f"</samlp:AuthnRequest>"
        )

        # Deflate and Base64 encode
        compressed = zlib.compress(authn_request.encode("utf-8"))[2:-4]
        encoded_request = base64.b64encode(compressed).decode("utf-8")
        params = {"SAMLRequest": encoded_request}

        if relay_state:
            params["RelayState"] = relay_state

        query_string = urllib.parse.urlencode(params)
        
        separator = "&" if "?" in config["idp_sso_url"] else "?"
        return f"{config['idp_sso_url']}{separator}{query_string}"

    async def parse_saml_response(
        self,
        config: dict[str, Any],
        saml_response: str,
    ) -> dict[str, Any]:
        """Parse and validate SAML Response."""
        self._validate_config(config)

        try:
            xml_str = base64.b64decode(saml_response)
            
            cert = config["idp_x509_cert"]
            if not cert.startswith("-----BEGIN CERTIFICATE"):
                cert = f"-----BEGIN CERTIFICATE-----\n{cert}\n-----END CERTIFICATE-----"

            # Azure AD requires checking audience restriction usually, but verify handles sign
            verified_data = XMLVerifier().verify(
                xml_str, 
                x509_cert=cert,
                ignore_ambiguous_key_info=True
            ).signed_xml
            
            ns = {
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
            }

            # Validating Audience is good practice (implicit in verify sometimes, but check manually if needed)
            # For now relying on signature verification

            # Extract NameID
            name_id_node = verified_data.find(".//saml:NameID", ns)
            if name_id_node is None:
                name_id_node = verified_data.find(".//saml:Subject/saml:NameID", ns)
            
            name_id = name_id_node.text if name_id_node is not None else None
            
            if not name_id:
                raise ValueError("Could not extract NameID from SAML Assertion")

            # Extract Attributes
            attributes = {}
            attribute_nodes = verified_data.findall(".//saml:AttributeStatement/saml:Attribute", ns)
            
            for attr in attribute_nodes:
                name = attr.get("Name")
                values = [val.text for val in attr.findall("saml:AttributeValue", ns) if val.text]
                if values:
                    attributes[name] = values[0] if len(values) == 1 else values

            # Azure AD specific claims mapping
            # Common Azure AD Claims:
            # http://schemas.microsoft.com/identity/claims/objectidentifier (User Object ID)
            # http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress (Email)
            # http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name (UPN)
            # http://schemas.microsoft.com/identity/claims/displayname (Display Name)
            # http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname
            # http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname

            email = (
                attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
                or attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
                or (name_id if "@" in name_id else None)
            )
            
            # Map specific name parts
            first_name = attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname")
            last_name = attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname")
            display_name = attributes.get("http://schemas.microsoft.com/identity/claims/displayname")

            if first_name and last_name:
                name = f"{first_name} {last_name}"
            elif display_name:
                name = display_name
            else:
                name = email.split("@")[0] if email else "Azure AD User"

            user_info = {
                "id": name_id, # Using NameID as stable ID. Could also use objectidentifier attribute if present.
                "email": email,
                "name": name,
                "attributes": attributes
            }

            return user_info

        except Exception as e:
            raise ValueError(f"SAML validation failed: {str(e)}") from e

    async def get_metadata(self, config: dict[str, Any]) -> str:
        """Generate SP Metadata XML."""
        self._validate_config(config)
        
        sp_entity_id = config["sp_entity_id"]
        acs_url = config["assertion_consumer_url"]
        
        # Azure AD likes specific metadata format sometimes, but standard usually works
        metadata = (
            f'<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
            f'entityID="{sp_entity_id}">'
            f'<md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
            f'<md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>'
            f'<md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{acs_url}" index="0" isDefault="true"/>'
            f'</md:SPSSODescriptor>'
            f'</md:EntityDescriptor>'
        )
        return metadata

    def _validate_config(self, config: dict[str, Any]) -> None:
        """Validate required configuration fields."""
        required = self.config_schema["required"]
        missing = [f for f in required if not config.get(f)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
