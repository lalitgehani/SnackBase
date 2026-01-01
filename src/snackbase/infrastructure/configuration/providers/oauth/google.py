"""Google OAuth 2.0 provider handler implementation."""

from typing import Any, Dict, Optional
import httpx
from snackbase.infrastructure.configuration.providers.oauth.oauth_handler import (
    OAuthProviderHandler,
)


class GoogleOAuthHandler(OAuthProviderHandler):
    """Google OAuth 2.0 authentication provider.

    Implements the OAuth 2.0 authorization code flow for Google, supporting
    PKCE, offline access (refresh tokens), and basic profile/email information.
    """

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google"

    @property
    def logo_url(self) -> str:
        return "/assets/providers/google.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "title": "Client ID",
                    "description": "Google OAuth 2.0 Client ID",
                },
                "client_secret": {
                    "type": "string",
                    "title": "Client Secret",
                    "description": "Google OAuth 2.0 Client Secret",
                    "secret": True,
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": "Scopes",
                    "description": "OAuth scopes (e.g., openid, email, profile)",
                    "default": ["openid", "email", "profile"],
                },
                "redirect_uri": {
                    "type": "string",
                    "title": "Redirect URI",
                    "description": "OAuth callback URL (must match Google Console)",
                },
            },
            "required": ["client_id", "client_secret", "scopes", "redirect_uri"],
        }

    async def get_authorization_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = "S256",
    ) -> str:
        """Generate Google OAuth 2.0 authorization URL."""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        
        scopes = " ".join(config.get("scopes", ["openid", "email", "profile"]))
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
            
        from urllib.parse import urlencode
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        config: Dict[str, Any],
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
            
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise ValueError(f"Failed to exchange Google OAuth code: {error_msg}")
            
            return response.json()

    async def get_user_info(
        self,
        config: Dict[str, Any],
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch user information from Google UserInfo V2 endpoint."""
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_url, headers=headers)
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Unknown error"))
                raise ValueError(f"Failed to fetch Google user info: {error_msg}")
            
            data = response.json()
            
            return {
                "id": str(data.get("id")),
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "verified_email": data.get("verified_email", False),
            }

    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """Validate Google OAuth configuration."""
        discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Test discovery endpoint reachability
                response = await client.get(discovery_url)
                if response.status_code != 200:
                    raise ValueError(f"Failed to fetch Google discovery document: {response.status_code}")
                
                # 2. Basic configuration validation (check required fields)
                required = ["client_id", "client_secret", "redirect_uri"]
                for field in required:
                    if not config.get(field):
                        raise ValueError(f"Missing required configuration field: {field}")
                
                return True
            except httpx.HTTPError as e:
                raise ValueError(f"Connectivity error to Google: {str(e)}") from e
            except Exception as e:
                raise ValueError(f"Configuration validation failed: {str(e)}") from e
