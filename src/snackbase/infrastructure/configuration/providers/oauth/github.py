"""GitHub OAuth 2.0 provider handler implementation."""

from typing import Any, Dict, List, Optional
import httpx
from snackbase.infrastructure.configuration.providers.oauth.oauth_handler import (
    OAuthProviderHandler,
)


class GitHubOAuthHandler(OAuthProviderHandler):
    """GitHub OAuth 2.0 authentication provider.

    Implements the OAuth 2.0 authorization code flow for GitHub, supporting
    basic profile and email information.
    """

    @property
    def provider_name(self) -> str:
        return "github"

    @property
    def display_name(self) -> str:
        return "GitHub"

    @property
    def logo_url(self) -> str:
        return "/assets/providers/github.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "title": "Client ID",
                    "description": "GitHub OAuth App Client ID",
                },
                "client_secret": {
                    "type": "string",
                    "title": "Client Secret",
                    "description": "GitHub OAuth App Client Secret",
                    "secret": True,
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": "Scopes",
                    "description": "OAuth scopes (e.g., user:email)",
                    "default": ["user:email"],
                },
                "redirect_uri": {
                    "type": "string",
                    "title": "Redirect URI",
                    "description": "OAuth callback URL (must match GitHub App)",
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
        """Generate GitHub OAuth 2.0 authorization URL."""
        base_url = "https://github.com/login/oauth/authorize"
        
        scopes = ",".join(config.get("scopes", ["user:email"]))
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
        }
        
        from urllib.parse import urlencode
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        config: Dict[str, Any],
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        token_url = "https://github.com/login/oauth/access_token"
        
        data = {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": redirect_uri,
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", error_data.get("error", error_msg))
                except Exception:
                    pass
                raise ValueError(f"Failed to exchange GitHub OAuth code: {error_msg}")
            
            data = response.json()
            if "error" in data:
                error_msg = data.get("error_description", data.get("error"))
                raise ValueError(f"Failed to exchange GitHub OAuth code: {error_msg}")
                
            return data

    async def get_user_info(
        self,
        config: Dict[str, Any],
        access_token: str,
    ) -> Dict[str, Any]:
        """Fetch user information from GitHub /user and /user/emails endpoints."""
        user_url = "https://api.github.com/user"
        emails_url = "https://api.github.com/user/emails"
        
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        async with httpx.AsyncClient() as client:
            # 1. Fetch basic user info
            user_response = await client.get(user_url, headers=headers)
            if user_response.status_code != 200:
                raise ValueError(f"Failed to fetch GitHub user info: {user_response.status_code}")
            user_data = user_response.json()
            
            # 2. Fetch email addresses
            emails_response = await client.get(emails_url, headers=headers)
            if emails_response.status_code != 200:
                raise ValueError(f"Failed to fetch GitHub user emails: {emails_response.status_code}")
            emails_data = emails_response.json()
            
            # 3. Find primary verified email
            primary_email = None
            for email_info in emails_data:
                if email_info.get("primary") and email_info.get("verified"):
                    primary_email = email_info.get("email")
                    break
            
            # Fallback to any verified email if primary not found
            if not primary_email:
                for email_info in emails_data:
                    if email_info.get("verified"):
                        primary_email = email_info.get("email")
                        break
            
            # Fallback to the first email if still not found
            if not primary_email and emails_data:
                primary_email = emails_data[0].get("email")

            return {
                "id": str(user_data.get("id")),
                "email": primary_email,
                "name": user_data.get("name") or user_data.get("login"),
                "picture": user_data.get("avatar_url"),
            }

    async def test_connection(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate GitHub OAuth configuration by checking required fields and API reachability."""
        api_url = "https://api.github.com"
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Test API reachability
                response = await client.get(api_url)
                if response.status_code != 200:
                    return False, f"Failed to reach GitHub API: {response.status_code}"
                
                # 2. Basic configuration validation (check required fields)
                required = ["client_id", "client_secret", "redirect_uri"]
                for field in required:
                    if not config.get(field):
                        return False, f"Missing required configuration field: {field}"
                
                return True, "GitHub connection successful. API reached."
            except httpx.HTTPError as e:
                return False, f"Connectivity error to GitHub: {str(e)}"
            except Exception as e:
                return False, f"Configuration validation failed: {str(e)}"
