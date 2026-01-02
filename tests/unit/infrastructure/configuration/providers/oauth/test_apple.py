"""Unit tests for AppleOAuthHandler."""

import pytest
from unittest.mock import MagicMock, patch
import httpx
import jwt
import time
from snackbase.infrastructure.configuration.providers.oauth.apple import AppleOAuthHandler


class TestAppleOAuthHandler:
    """Test suite for AppleOAuthHandler."""

    @pytest.fixture
    def handler(self):
        return AppleOAuthHandler()

    @pytest.fixture
    def config(self):
        return {
            "client_id": "test_client_id",
            "client_secret": "test_private_key_content",
            "team_id": "test_team_id",
            "key_id": "test_key_id",
            "scopes": ["name", "email"],
            "redirect_uri": "https://example.com/callback",
        }

    def test_metadata_properties(self, handler):
        """Test provider metadata properties."""
        assert handler.provider_name == "apple"
        assert handler.display_name == "Apple"
        assert handler.logo_url == "/assets/providers/apple.svg"
        assert handler.provider_type == "oauth2"

    def test_config_schema(self, handler):
        """Test configuration schema structure."""
        schema = handler.config_schema
        assert schema["type"] == "object"
        assert "client_id" in schema["required"]
        assert "client_secret" in schema["required"]
        assert "team_id" in schema["required"]
        assert "key_id" in schema["required"]
        assert "redirect_uri" in schema["required"]
        assert schema["properties"]["client_secret"]["secret"] is True

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, handler, config):
        """Test authorization URL generation."""
        state = "test_state"
        redirect_uri = "https://app.com/callback"
        
        url = await handler.get_authorization_url(config, redirect_uri, state)
        
        assert "appleid.apple.com/auth/authorize" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.com%2Fcallback" in url
        assert "state=test_state" in url
        assert "scope=name+email" in url
        assert "response_type=code" in url
        assert "response_mode=form_post" in url

    @patch("jwt.encode")
    def test_generate_client_secret(self, mock_jwt_encode, handler, config):
        """Test JWT client secret generation."""
        mock_jwt_encode.return_value = "fake_jwt_token"
        
        secret = handler._generate_client_secret(config)
        
        assert secret == "fake_jwt_token"
        assert mock_jwt_encode.called
        
        # Verify jwt.encode call parameters
        args, kwargs = mock_jwt_encode.call_args
        payload = args[0]
        assert payload["iss"] == "test_team_id"
        assert payload["sub"] == "test_client_id"
        assert payload["aud"] == "https://appleid.apple.com"
        assert kwargs["headers"]["kid"] == "test_key_id"
        assert kwargs["algorithm"] == "ES256"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    @patch("snackbase.infrastructure.configuration.providers.oauth.apple.AppleOAuthHandler._generate_client_secret")
    async def test_exchange_code_for_tokens_success(self, mock_gen_secret, mock_post, handler, config):
        """Test successful token exchange."""
        mock_gen_secret.return_value = "fake_jwt_secret"
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "id_token": "test_id_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        
        tokens = await handler.exchange_code_for_tokens(
            config, "auth_code", "https://example.com/callback"
        )
        
        assert tokens["access_token"] == "test_access_token"
        assert tokens["id_token"] == "test_id_token"
        
        # Verify call parameters
        args, kwargs = mock_post.call_args
        assert args[0] == "https://appleid.apple.com/auth/token"
        assert kwargs["data"]["code"] == "auth_code"
        assert kwargs["data"]["client_id"] == "test_client_id"
        assert kwargs["data"]["client_secret"] == "fake_jwt_secret"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    @patch("snackbase.infrastructure.configuration.providers.oauth.apple.AppleOAuthHandler._generate_client_secret")
    async def test_exchange_code_for_tokens_failure(self, mock_gen_secret, mock_post, handler, config):
        """Test token exchange failure."""
        mock_gen_secret.return_value = "fake_jwt_secret"
        
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant", "error_description": "Invalid code"}
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Failed to exchange Apple OAuth code: Invalid code"):
            await handler.exchange_code_for_tokens(
                config, "invalid_code", "https://example.com/callback"
            )

    @pytest.mark.asyncio
    @patch("jwt.decode")
    async def test_get_user_info_success(self, mock_jwt_decode, handler, config):
        """Test successful user info retrieval from id_token."""
        mock_jwt_decode.return_value = {
            "sub": "apple_user_123",
            "email": "user@apple.com",
            "email_verified": "true",
        }
        
        user_info = await handler.get_user_info(config, "fake_id_token")
        
        assert user_info["id"] == "apple_user_123"
        assert user_info["email"] == "user@apple.com"
        assert user_info["verified_email"] is True
        
        # Verify decode call
        mock_jwt_decode.assert_called_with("fake_id_token", options={"verify_signature": False})

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, handler, config):
        """Test user info retrieval failure with invalid token."""
        with pytest.raises(ValueError, match="Failed to decode Apple id_token"):
            await handler.get_user_info(config, "invalid_token_no_dots")

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
        assert "appleid.apple.com/.well-known/openid-configuration" in args[0]

        invalid_config = {"client_id": "missing_other_fields"}
        result, message = await handler.test_connection(invalid_config)
        assert result is False
        assert "Missing required configuration field" in message
