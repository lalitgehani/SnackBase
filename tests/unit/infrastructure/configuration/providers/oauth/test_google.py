"""Unit tests for GoogleOAuthHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from snackbase.infrastructure.configuration.providers.oauth.google import GoogleOAuthHandler


class TestGoogleOAuthHandler:
    """Test suite for GoogleOAuthHandler."""

    @pytest.fixture
    def handler(self):
        return GoogleOAuthHandler()

    @pytest.fixture
    def config(self):
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["openid", "email", "profile"],
            "redirect_uri": "https://example.com/callback",
        }

    def test_metadata_properties(self, handler):
        """Test provider metadata properties."""
        assert handler.provider_name == "google"
        assert handler.display_name == "Google"
        assert handler.logo_url == "/assets/providers/google.svg"
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
        
        assert "accounts.google.com" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.com%2Fcallback" in url
        assert "state=test_state" in url
        assert "scope=openid+email+profile" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    @pytest.mark.asyncio
    async def test_get_authorization_url_with_pkce(self, handler, config):
        """Test authorization URL generation with PKCE."""
        state = "test_state"
        redirect_uri = "https://app.com/callback"
        code_challenge = "test_challenge"
        
        url = await handler.get_authorization_url(
            config, redirect_uri, state, code_challenge=code_challenge
        )
        
        assert "code_challenge=test_challenge" in url
        assert "code_challenge_method=S256" in url

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_tokens_success(self, mock_post, handler, config):
        """Test successful token exchange."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "id_token": "test_id_token",
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response
        
        tokens = await handler.exchange_code_for_tokens(
            config, "auth_code", "https://example.com/callback"
        )
        
        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"
        assert tokens["id_token"] == "test_id_token"
        
        # Verify call parameters
        args, kwargs = mock_post.call_args
        assert args[0] == "https://oauth2.googleapis.com/token"
        assert kwargs["data"]["code"] == "auth_code"
        assert kwargs["data"]["client_id"] == "test_client_id"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_tokens_failure(self, mock_post, handler, config):
        """Test token exchange failure."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant", "error_description": "Invalid code"}
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Failed to exchange Google OAuth code: Invalid code"):
            await handler.exchange_code_for_tokens(
                config, "invalid_code", "https://example.com/callback"
            )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_user_info_success(self, mock_get, handler, config):
        """Test successful user info retrieval."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "email": "user@google.com",
            "name": "Google User",
            "picture": "https://goog.com/pic.jpg",
            "verified_email": True,
        }
        mock_get.return_value = mock_response
        
        user_info = await handler.get_user_info(config, "test_token")
        
        assert user_info["id"] == "12345"
        assert user_info["email"] == "user@google.com"
        assert user_info["name"] == "Google User"
        assert user_info["picture"] == "https://goog.com/pic.jpg"
        assert user_info["verified_email"] is True
        
        # Verify call parameters
        args, kwargs = mock_get.call_args
        assert args[0] == "https://www.googleapis.com/oauth2/v2/userinfo"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_test_connection_success(self, mock_get, handler, config):
        """Test successful connection validation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = await handler.test_connection(config)
        assert result is True
        
        # Verify it called the discovery endpoint
        args, _ = mock_get.call_args
        assert "openid-configuration" in args[0]

    @pytest.mark.asyncio
    async def test_test_connection_invalid_config(self, handler):
        """Test connection validation with invalid config."""
        invalid_config = {"client_id": "missing_other_fields"}
        
        with pytest.raises(ValueError, match="Missing required configuration field"):
            await handler.test_connection(invalid_config)
