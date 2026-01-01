"""Unit tests for GitHubOAuthHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from snackbase.infrastructure.configuration.providers.oauth.github import GitHubOAuthHandler


class TestGitHubOAuthHandler:
    """Test suite for GitHubOAuthHandler."""

    @pytest.fixture
    def handler(self):
        return GitHubOAuthHandler()

    @pytest.fixture
    def config(self):
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["user:email"],
            "redirect_uri": "https://example.com/callback",
        }

    def test_metadata_properties(self, handler):
        """Test provider metadata properties."""
        assert handler.provider_name == "github"
        assert handler.display_name == "GitHub"
        assert handler.logo_url == "/assets/providers/github.svg"
        assert handler.provider_type == "oauth2"

    def test_config_schema(self, handler):
        """Test configuration schema structure."""
        schema = handler.config_schema
        assert schema["type"] == "object"
        assert "client_id" in schema["required"]
        assert "client_secret" in schema["required"]
        assert "scopes" in schema["required"]
        assert "redirect_uri" in schema["required"]
        assert schema["properties"]["client_secret"]["secret"] is True

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, handler, config):
        """Test authorization URL generation."""
        state = "test_state"
        redirect_uri = "https://app.com/callback"
        
        url = await handler.get_authorization_url(config, redirect_uri, state)
        
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.com%2Fcallback" in url
        assert "state=test_state" in url
        assert "scope=user%3Aemail" in url

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_tokens_success(self, mock_post, handler, config):
        """Test successful token exchange."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "bearer",
            "scope": "user:email",
        }
        mock_post.return_value = mock_response
        
        tokens = await handler.exchange_code_for_tokens(
            config, "auth_code", "https://example.com/callback"
        )
        
        assert tokens["access_token"] == "test_access_token"
        
        # Verify call parameters
        args, kwargs = mock_post.call_args
        assert args[0] == "https://github.com/login/oauth/access_token"
        assert kwargs["data"]["code"] == "auth_code"
        assert kwargs["headers"]["Accept"] == "application/json"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_tokens_failure(self, mock_post, handler, config):
        """Test token exchange failure."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200  # GitHub returns 200 even for some errors
        mock_response.json.return_value = {"error": "bad_verification_code", "error_description": "The code passed is incorrect or expired."}
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Failed to exchange GitHub OAuth code: The code passed is incorrect or expired."):
            await handler.exchange_code_for_tokens(
                config, "invalid_code", "https://example.com/callback"
            )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_user_info_success(self, mock_get, handler, config):
        """Test successful user info retrieval."""
        # 1. Mock user info response
        user_response = MagicMock(spec=httpx.Response)
        user_response.status_code = 200
        user_response.json.return_value = {
            "id": 12345,
            "login": "githubuser",
            "name": "GitHub User",
            "avatar_url": "https://github.com/pic.jpg",
        }
        
        # 2. Mock emails response
        emails_response = MagicMock(spec=httpx.Response)
        emails_response.status_code = 200
        emails_response.json.return_value = [
            {"email": "other@github.com", "primary": False, "verified": True},
            {"email": "user@github.com", "primary": True, "verified": True},
        ]
        
        mock_get.side_effect = [user_response, emails_response]
        
        user_info = await handler.get_user_info(config, "test_token")
        
        assert user_info["id"] == "12345"
        assert user_info["email"] == "user@github.com"
        assert user_info["name"] == "GitHub User"
        assert user_info["picture"] == "https://github.com/pic.jpg"
        
        # Verify call parameters
        assert mock_get.call_count == 2
        calls = mock_get.call_args_list
        assert calls[0][0][0] == "https://api.github.com/user"
        assert calls[1][0][0] == "https://api.github.com/user/emails"
        assert calls[0][1]["headers"]["Authorization"] == "token test_token"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_test_connection_success(self, mock_get, handler, config):
        """Test successful connection validation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = await handler.test_connection(config)
        assert result is True
        
        # Verify it called the API root
        args, _ = mock_get.call_args
        assert args[0] == "https://api.github.com"

    @pytest.mark.asyncio
    async def test_test_connection_invalid_config(self, handler):
        """Test connection validation with invalid config."""
        # Missing client_secret
        invalid_config = {"client_id": "test", "redirect_uri": "test"}
        
        with pytest.raises(ValueError, match="Missing required configuration field"):
            await handler.test_connection(invalid_config)
