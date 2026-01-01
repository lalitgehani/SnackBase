"""SAML 2.0 provider handler base class.

This module defines the abstract base class for all SAML 2.0 authentication
providers, ensuring a consistent interface for authorization, response parsing,
and metadata generation.
"""

import abc
from typing import Any


class SAMLProviderHandler(abc.ABC):
    """Abstract base class for SAML 2.0 authentication providers.

    All SAML providers (Okta, Azure AD, Generic) must implement this interface
    to ensure consistent behavior.

    The SAML flow consists of:
    1. Generate authorization URL (SAML Request) to redirect user to IdP
    2. Receive SAML Response from IdP (via ACS endpoint)
    3. Parse and validate SAML Response to get user info
    4. Provide SP Metadata for IdP configuration
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'okta', 'azure_ad', 'generic_saml').

        Returns:
            Lowercase provider identifier used in URLs and configuration.
        """
        pass

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'Okta', 'Azure AD').

        Returns:
            Display name shown in UI and error messages.
        """
        pass

    @property
    @abc.abstractmethod
    def logo_url(self) -> str:
        """Path to provider logo asset.

        Returns:
            URL path to SVG logo (e.g., '/assets/providers/okta.svg').
        """
        pass

    @property
    def provider_type(self) -> str:
        """Provider type identifier.

        Returns:
            Always returns 'saml' for SAML providers.
        """
        return "saml"

    @property
    @abc.abstractmethod
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for provider configuration validation.

        Must include at minimum:
        - idp_entity_id: Identity Provider Entity ID
        - idp_sso_url: Identity Provider SSO URL
        - idp_x509_cert: Identity Provider X.509 Certificate
        - sp_entity_id: Service Provider (SnackBase) Entity ID
        - assertion_consumer_url: URL to receive SAML assertions

        Returns:
            JSON Schema dictionary for validating provider configuration.
        """
        pass

    @abc.abstractmethod
    async def get_authorization_url(
        self,
        config: dict[str, Any],
        redirect_uri: str,
        relay_state: str | None = None,
    ) -> str:
        """Generate SAML authorization URL to redirect user to IdP.

        Constructs a SAML 2.0 AuthnRequest and encodes it for the IdP's
        SSO Service URL (usually HTTP-Redirect binding).

        Args:
            config: Provider configuration.
            redirect_uri: The ACS URL (used as AssertionConsumerServiceURL in request).
            relay_state: Optional state to preserve through the flow.

        Returns:
            Complete URL to redirect user to.

        Raises:
            ValueError: If configuration is invalid.
        """
        pass

    @abc.abstractmethod
    async def parse_saml_response(
        self,
        config: dict[str, Any],
        saml_response: str,
    ) -> dict[str, Any]:
        """Parse and validate a SAML Response from the IdP.

        Validates the signature using idp_x509_cert, checks conditions/timestamps,
        and extracts user attributes.

        Args:
            config: Provider configuration.
            saml_response: Base64 encoded SAMLResponse string from POST body.

        Returns:
            Dictionary containing user information:
            - id (str): User identifier (NameID)
            - email (str, optional): User email if available
            - name (str, optional): User name if available
            - attributes (dict): All raw SAML attributes

        Raises:
            ValueError: If validation fails or parsing errors occur.
        """
        pass

    @abc.abstractmethod
    async def get_metadata(self, config: dict[str, Any]) -> str:
        """Generate SAML 2.0 Service Provider (SP) Metadata XML.

        Used to configure the IdP to recognize SnackBase as a valid SP.

        Args:
            config: Provider configuration.

        Returns:
            XML string containing the SP metadata.
        """
        pass

    async def test_connection(self, config: dict[str, Any]) -> bool:
        """Test if provider configuration is valid.

        Default implementation attempts to generate metadata.
        Subclasses can override for more specific validation.

        Args:
            config: Provider configuration to validate.

        Returns:
            True if configuration is valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        try:
            # Try to generate metadata - this validates most required config fields
            await self.get_metadata(config)
            return True
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e
