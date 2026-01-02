"""Unit tests for MicrosoftOAuthHandler."""

import pytest
from unittest.mock import MagicMock, patch
import httpx
from snackbase.infrastructure.configuration.providers.oauth.microsoft import MicrosoftOAuthHandler


class TestMicrosoftOAuthHandler:
    """Test suite for MicrosoftOAuthHandler."""

    @pytest.fixture
    def handler(self):
        return MicrosoftOAuthHandler()

    @pytest.fixture
    def config(self):
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "tenant_id": "common",
            "scopes": ["openid", "email", "profile", "User.Read"],
            "redirect_uri": "https://example.com/callback",
        }

    def test_metadata_properties(self, handler):
        """Test provider metadata properties."""
        assert handler.provider_name == "microsoft"
        assert handler.display_name == "Microsoft"
        assert handler.logo_url == "/assets/providers/microsoft.svg"
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
        assert schema["properties"]["tenant_id"]["default"] == "common"

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, handler, config):
        """Test authorization URL generation."""
        state = "test_state"
        redirect_uri = "https://app.com/callback"
        
        url = await handler.get_authorization_url(config, redirect_uri, state)
        
        assert "login.microsoftonline.com/common/oauth2/v2.0/authorize" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.com%2Fcallback" in url
        assert "state=test_state" in url
        assert "scope=openid+email+profile+User.Read" in url
        assert "response_type=code" in url
        assert "response_mode=query" in url

    @pytest.mark.asyncio
    async def test_get_authorization_url_with_tenant(self, handler, config):
        """Test authorization URL generation with custom tenant."""
        config["tenant_id"] = "my_tenant"
        state = "test_state"
        redirect_uri = "https://app.com/callback"
        
        url = await handler.get_authorization_url(config, redirect_uri, state)
        
        assert "login.microsoftonline.com/my_tenant/oauth2/v2.0/authorize" in url

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
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response
        
        tokens = await handler.exchange_code_for_tokens(
            config, "auth_code", "https://example.com/callback"
        )
        
        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"
        
        # Verify call parameters
        args, kwargs = mock_post.call_args
        assert args[0] == "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        assert kwargs["data"]["code"] == "auth_code"
        assert kwargs["data"]["client_id"] == "test_client_id"
        assert kwargs["data"]["client_secret"] == "test_client_secret"
        assert kwargs["data"]["grant_type"] == "authorization_code"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_tokens_failure(self, mock_post, handler, config):
        """Test token exchange failure."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant", "error_description": "Invalid code"}
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Failed to exchange Microsoft OAuth code: Invalid code"):
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
            "mail": "user@microsoft.com",
            "displayName": "Microsoft User",
            "userPrincipalName": "user_upn@microsoft.com",
        }
        mock_get.return_value = mock_response
        
        user_info = await handler.get_user_info(config, "test_token")
        
        assert user_info["id"] == "12345"
        assert user_info["email"] == "user@microsoft.com"
        assert user_info["name"] == "Microsoft User"
        assert user_info["picture"] is None
        
        # Verify call parameters
        args, kwargs = mock_get.call_args
        assert args[0] == "https://graph.microsoft.com/v1.0/me"
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_user_info_upn_fallback(self, mock_get, handler, config):
        """Test user info retrieval with UPN fallback when mail is missing."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "mail": None,
            "displayName": "Microsoft User",
            "userPrincipalName": "user_upn@microsoft.com",
        }
        mock_get.return_value = mock_response
        
        user_info = await handler.get_user_info(config, "test_token")
        assert user_info["email"] == "user_upn@microsoft.com"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_test_connection_success(self, mock_get, handler, config):
        """Test successful connection validation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result, message = await handler.test_connection(config)
        assert result is True
        assert "Discovery endpoint reached" in message
        
        # Verify it called the discovery endpoint
        args, _ = mock_get.call_args
        assert "login.microsoftonline.com/common/v2.0/.well-known/openid-configuration" in args[0]

        invalid_config = {"client_id": "missing_other_fields"}
        result, message = await handler.test_connection(invalid_config)
        assert result is False
        assert "Missing required configuration field" in message
