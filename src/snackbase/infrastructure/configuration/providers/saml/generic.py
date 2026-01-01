"""Generic SAML 2.0 provider handler."""

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


class GenericSAMLProvider(SAMLProviderHandler):
    """Generic SAML 2.0 authentication provider.

    Allows configuration of any SAML 2.0 compliant Identity Provider.
    """

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "generic_saml"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "SAML 2.0"

    @property
    def logo_url(self) -> str:
        """Path to provider logo asset."""
        return "/assets/providers/saml.svg"

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
                    "title": "IdP Entity ID (Issuer URI)",
                },
                "idp_sso_url": {
                    "type": "string",
                    "title": "IdP Single Sign-On URL",
                    "format": "uri",
                },
                "idp_x509_cert": {
                    "type": "string",
                    "title": "IdP X.509 Certificate",
                    "description": "The public certificate of the Identity Provider",
                },
                "sp_entity_id": {
                    "type": "string",
                    "title": "SP Entity ID",
                    "description": "The Audience URI for this SP",
                },
                "assertion_consumer_url": {
                    "type": "string",
                    "title": "Assertion Consumer Service (ACS) URL",
                    "format": "uri",
                },
                "binding": {
                    "type": "string",
                    "title": "Request Binding",
                    "enum": ["HTTP-Redirect", "HTTP-POST"],
                    "default": "HTTP-Redirect",
                },
                "name_id_format": {
                    "type": "string",
                    "title": "NameID Format",
                    "default": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
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

        # Default to HTTP-Redirect for simpler URL generation
        # (HTTP-POST requires returning a form to auto-submit)
        # For now, we only implement HTTP-Redirect binding for the request
        # regardless of the config, as it's the standard for authn requests.
        # If POST support is needed for requests, it would require a different return type.

        issue_instant = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        request_id = f"id_{secrets.token_hex(16)}"
        sp_entity_id = config["sp_entity_id"]
        acs_url = config.get("assertion_consumer_url", redirect_uri)
        name_id_format = config.get(
            "name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        )

        # Build AuthnRequest XML
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
            f'<samlp:NameIDPolicy Format="{name_id_format}" AllowCreate="true" />'
            f"</samlp:AuthnRequest>"
        )

        # Deflate and Base64 encode for HTTP-Redirect
        compressed = zlib.compress(authn_request.encode("utf-8"))[2:-4]  # Raw deflate
        encoded_request = base64.b64encode(compressed).decode("utf-8")
        params = {"SAMLRequest": encoded_request}

        if relay_state:
            params["RelayState"] = relay_state

        query_string = urllib.parse.urlencode(params)
        
        # Determine separator
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
            # Decode Base64
            xml_str = base64.b64decode(saml_response)
            
            # Format certificate
            cert = config["idp_x509_cert"]
            if not cert.startswith("-----BEGIN CERTIFICATE"):
                cert = f"-----BEGIN CERTIFICATE-----\n{cert}\n-----END CERTIFICATE-----"

            # Verify signature
            verified_data = XMLVerifier().verify(
                xml_str, 
                x509_cert=cert,
                ignore_ambiguous_key_info=True
            ).signed_xml

            # Namespaces
            ns = {
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
            }

            # Extract NameID
            name_id_node = verified_data.find(".//saml:NameID", ns)
            if name_id_node is None:
                # Fallback to Subject/NameID
                name_id_node = verified_data.find(".//saml:Subject/saml:NameID", ns)
            
            name_id = name_id_node.text if name_id_node is not None else None
            
            if not name_id:
                raise ValueError("Could not extract NameID from SAML Assertion")

            # Extract Attributes
            attributes = {}
            attribute_nodes = verified_data.findall(".//saml:AttributeStatement/saml:Attribute", ns)
            
            for attr in attribute_nodes:
                name = attr.get("Name")
                if not name:
                    continue
                    
                # Get the value(s)
                values = [val.text for val in attr.findall("saml:AttributeValue", ns) if val.text]
                if values:
                    attributes[name] = values[0] if len(values) == 1 else values

            # Map to user info
            user_info = {
                "id": name_id,
                # Try to use NameID as email if it looks like one
                "email": name_id if "@" in name_id else None,
                "attributes": attributes
            }

            # Try to resolve email from attributes if not in NameID or to valid it
            # Common email attribute names
            email_keys = ["email", "Email", "mail", "User.Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"]
            for key in email_keys:
                if key in attributes:
                    val = attributes[key]
                    if isinstance(val, list):
                        val = val[0]
                    if val and "@" in str(val):
                        user_info["email"] = str(val)
                        break

            # Try to resolve name
            name_parts = []
            
            # First name
            first_name_keys = ["firstName", "givenName", "gn", "User.FirstName", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"]
            for key in first_name_keys:
                if key in attributes:
                    val = attributes[key]
                    if isinstance(val, list):
                        val = val[0]
                    if val:
                        name_parts.append(str(val))
                        break
            
            # Last name
            last_name_keys = ["lastName", "sn", "surname", "User.LastName", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"]
            for key in last_name_keys:
                if key in attributes:
                    val = attributes[key]
                    if isinstance(val, list):
                        val = val[0]
                    if val:
                        name_parts.append(str(val))
                        break
            
            if name_parts:
                user_info["name"] = " ".join(name_parts)
            else:
                # Try DisplayName
                display_name_keys = ["displayName", "cn", "commonName", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"]
                for key in display_name_keys:
                    if key in attributes:
                        val = attributes[key]
                        if isinstance(val, list):
                            val = val[0]
                        if val:
                            user_info["name"] = str(val)
                            break

            return user_info

        except Exception as e:
            raise ValueError(f"SAML validation failed: {str(e)}") from e

    async def get_metadata(self, config: dict[str, Any]) -> str:
        """Generate SP Metadata XML."""
        self._validate_config(config)
        
        sp_entity_id = config["sp_entity_id"]
        acs_url = config["assertion_consumer_url"]
        name_id_format = config.get(
            "name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        )
        
        metadata = (
            f'<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
            f'entityID="{sp_entity_id}">'
            f'<md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
            f'<md:NameIDFormat>{name_id_format}</md:NameIDFormat>'
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
