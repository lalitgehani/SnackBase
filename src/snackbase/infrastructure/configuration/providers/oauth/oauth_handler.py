"""OAuth 2.0 provider handler base class.

This module defines the abstract base class for all OAuth 2.0 authentication
providers, ensuring a consistent interface for authorization, token exchange,
and user information retrieval.
"""

import abc
from typing import Any


class OAuthProviderHandler(abc.ABC):
    """Abstract base class for OAuth 2.0 authentication providers.

    All OAuth providers must implement this interface to ensure consistent
    behavior across different OAuth providers (Google, GitHub, Microsoft, Apple, etc.).

    The OAuth flow consists of three main steps:
    1. Generate authorization URL to redirect user to provider
    2. Exchange authorization code for access/refresh tokens
    3. Fetch user information using the access token
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'google', 'github', 'microsoft').

        Returns:
            Lowercase provider identifier used in URLs and configuration.
        """
        pass

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'Google', 'GitHub').

        Returns:
            Display name shown in UI and error messages.
        """
        pass

    @property
    @abc.abstractmethod
    def logo_url(self) -> str:
        """Path to provider logo asset.

        Returns:
            URL path to SVG logo (e.g., '/assets/providers/google.svg').
        """
        pass

    @property
    def provider_type(self) -> str:
        """Provider type identifier.

        Returns:
            Always returns 'oauth2' for OAuth providers.
        """
        return "oauth2"

    @property
    @abc.abstractmethod
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for provider configuration validation.

        Must include at minimum:
        - client_id: OAuth client ID (string, required)
        - client_secret: OAuth client secret (string, required, secret)
        - scopes: List of OAuth scopes (array of strings, required)
        - redirect_uri: OAuth callback URL (string, required)

        Returns:
            JSON Schema dictionary for validating provider configuration.
        """
        pass

    @abc.abstractmethod
    async def get_authorization_url(
        self,
        config: dict[str, Any],
        redirect_uri: str,
        state: str,
    ) -> str:
        """Generate OAuth authorization URL to redirect user to provider.

        This URL should include all necessary parameters for the OAuth flow:
        - client_id
        - redirect_uri
        - scope
        - state (CSRF protection)
        - response_type=code (authorization code flow)
        - Any provider-specific parameters

        Args:
            config: Provider configuration containing client_id, scopes, etc.
            redirect_uri: Callback URL where provider will redirect after auth.
            state: CSRF state token for security.

        Returns:
            Complete authorization URL to redirect user to.

        Raises:
            ValueError: If configuration is invalid or missing required fields.
        """
        pass

    @abc.abstractmethod
    async def exchange_code_for_tokens(
        self,
        config: dict[str, Any],
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.

        Makes a POST request to the provider's token endpoint with:
        - code: Authorization code from callback
        - client_id: OAuth client ID
        - client_secret: OAuth client secret
        - redirect_uri: Must match the one used in authorization
        - grant_type: authorization_code

        Args:
            config: Provider configuration containing client_id, client_secret, etc.
            code: Authorization code received from provider callback.
            redirect_uri: Callback URL (must match authorization request).

        Returns:
            Dictionary containing:
            - access_token (str): Access token for API requests
            - refresh_token (str, optional): Refresh token for token renewal
            - expires_in (int, optional): Token expiration in seconds
            - id_token (str, optional): OpenID Connect ID token
            - token_type (str, optional): Token type (usually 'Bearer')

        Raises:
            ValueError: If code exchange fails or returns an error.
            httpx.HTTPError: If network request fails.
        """
        pass

    @abc.abstractmethod
    async def get_user_info(
        self,
        config: dict[str, Any],
        access_token: str,
    ) -> dict[str, Any]:
        """Fetch user information from provider using access token.

        Makes a GET request to the provider's user info endpoint with
        the access token in the Authorization header.

        Args:
            config: Provider configuration.
            access_token: OAuth access token.

        Returns:
            Dictionary containing:
            - id (str): Provider's unique user identifier
            - email (str): User's email address
            - name (str): User's full name
            - picture (str, optional): URL to user's profile picture
            - Any additional provider-specific fields

        Raises:
            ValueError: If user info request fails or returns an error.
            httpx.HTTPError: If network request fails.
        """
        pass

    async def test_connection(self, config: dict[str, Any]) -> bool:
        """Test if provider configuration is valid.

        Default implementation attempts to construct an authorization URL
        with the provided configuration. Subclasses can override this
        for provider-specific validation (e.g., calling discovery endpoints).

        Args:
            config: Provider configuration to validate.

        Returns:
            True if configuration is valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        # Default implementation: try to generate authorization URL
        # This validates that required config fields are present
        try:
            await self.get_authorization_url(
                config=config,
                redirect_uri="https://example.com/callback",
                state="test_state",
            )
            return True
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e
