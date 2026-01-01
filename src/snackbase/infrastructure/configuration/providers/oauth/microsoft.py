"""Microsoft OAuth 2.0 provider handler implementation."""

from typing import Any, Dict, Optional
from urllib.parse import urlencode
import httpx
from snackbase.infrastructure.configuration.providers.oauth.oauth_handler import (
    OAuthProviderHandler,
)


class MicrosoftOAuthHandler(OAuthProviderHandler):
    """Microsoft OAuth 2.0 authentication provider.

    Implements the OAuth 2.0 authorization code flow for Microsoft Azure AD,
    supporting multi-tenant (common) or single-tenant authorization and
    basic profile/email information via Microsoft Graph API.
    """

    @property
    def provider_name(self) -> str:
        return "microsoft"

    @property
    def display_name(self) -> str:
        return "Microsoft"

    @property
    def logo_url(self) -> str:
        return "/assets/providers/microsoft.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "title": "Client ID",
                    "description": "Microsoft Application (client) ID",
                },
                "client_secret": {
                    "type": "string",
                    "title": "Client Secret",
                    "description": "Microsoft Client Secret",
                    "secret": True,
                },
                "tenant_id": {
                    "type": "string",
                    "title": "Tenant ID",
                    "description": "Azure AD Tenant ID (use 'common' for multi-tenant)",
                    "default": "common",
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": "Scopes",
                    "description": "OAuth scopes (e.g., openid, email, profile, User.Read)",
                    "default": ["openid", "email", "profile", "User.Read"],
                },
                "redirect_uri": {
                    "type": "string",
                    "title": "Redirect URI",
                    "description": "OAuth callback URL (must match Azure Portal)",
                },
            },
            "required": ["client_id", "client_secret", "scopes", "redirect_uri"],
        }

    async def get_authorization_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str,
    ) -> str:
        """Generate Microsoft OAuth 2.0 authorization URL."""
        tenant = config.get("tenant_id", "common")
        base_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"

        scopes = " ".join(config.get("scopes", ["openid", "email", "profile", "User.Read"]))

        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
            "response_mode": "query",
        }

        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        config: Dict[str, Any],
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        tenant = config.get("tenant_id", "common")
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

        scopes = " ".join(config.get("scopes", ["openid", "email", "profile", "User.Read"]))

        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": scopes,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                except Exception:
                    error_msg = response.text
                raise ValueError(f"Failed to exchange Microsoft OAuth code: {error_msg}")

            return response.json()

    async def get_user_info(
        self,
        config: Dict[str, Any],
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch user information from Microsoft Graph /me endpoint."""
        userinfo_url = "https://graph.microsoft.com/v1.0/me"

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_msg = response.text
                raise ValueError(f"Failed to fetch Microsoft user info: {error_msg}")

            data = response.json()

            # Microsoft Graph returns mail or userPrincipalName for email
            email = data.get("mail") or data.get("userPrincipalName")

            return {
                "id": str(data.get("id")),
                "email": email,
                "name": data.get("displayName"),
                "picture": None,  # Microsoft Graph requires separate call for photo
            }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """Validate Microsoft OAuth configuration."""
        tenant = config.get("tenant_id", "common")
        discovery_url = f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"

        async with httpx.AsyncClient() as client:
            try:
                # 1. Test discovery endpoint reachability
                response = await client.get(discovery_url)
                if response.status_code != 200:
                    raise ValueError(f"Failed to fetch Microsoft discovery document: {response.status_code}")

                # 2. Basic configuration validation (check required fields)
                required = ["client_id", "client_secret", "redirect_uri"]
                for field in required:
                    if not config.get(field):
                        raise ValueError(f"Missing required configuration field: {field}")

                return True
            except httpx.HTTPError as e:
                raise ValueError(f"Connectivity error to Microsoft: {str(e)}") from e
            except Exception as e:
                raise ValueError(f"Configuration validation failed: {str(e)}") from e
