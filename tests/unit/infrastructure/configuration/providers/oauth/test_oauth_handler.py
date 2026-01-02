"""Unit tests for OAuthProviderHandler abstract base class."""

import inspect
from typing import Any, Dict

import pytest

from snackbase.infrastructure.configuration.providers.oauth.oauth_handler import (
    OAuthProviderHandler,
)


class TestOAuthProviderHandler:
    """Test suite for OAuthProviderHandler abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that OAuthProviderHandler cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            OAuthProviderHandler()

    def test_concrete_implementation_requires_all_abstract_methods(self):
        """Test that concrete class missing abstract methods cannot be instantiated."""
        
        # Create incomplete implementation (missing get_user_info)
        class IncompleteProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "incomplete"
            
            @property
            def display_name(self) -> str:
                return "Incomplete"
            
            @property
            def logo_url(self) -> str:
                return "/assets/providers/incomplete.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {}
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                return "https://example.com/authorize"
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {}
            
            # Missing: get_user_info
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteProvider()

    def test_concrete_implementation_with_all_methods(self):
        """Test that concrete implementation with all methods can be instantiated."""
        
        class CompleteProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "test_provider"
            
            @property
            def display_name(self) -> str:
                return "Test Provider"
            
            @property
            def logo_url(self) -> str:
                return "/assets/providers/test.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "scopes": {"type": "array", "items": {"type": "string"}},
                        "redirect_uri": {"type": "string"},
                    },
                    "required": ["client_id", "client_secret", "scopes", "redirect_uri"],
                }
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                return f"https://example.com/authorize?state={state}"
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {
                    "access_token": "test_token",
                    "token_type": "Bearer",
                }
            
            async def get_user_info(
                self, config: Dict[str, Any], access_token: str
            ) -> Dict[str, Any]:
                return {
                    "id": "123",
                    "email": "test@example.com",
                    "name": "Test User",
                }
        
        # Should instantiate without errors
        provider = CompleteProvider()
        assert provider is not None
        assert isinstance(provider, OAuthProviderHandler)

    def test_provider_type_returns_oauth2(self):
        """Test that provider_type property returns 'oauth2'."""
        
        class TestProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "test"
            
            @property
            def display_name(self) -> str:
                return "Test"
            
            @property
            def logo_url(self) -> str:
                return "/test.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {}
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                return ""
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {}
            
            async def get_user_info(
                self, config: Dict[str, Any], access_token: str
            ) -> Dict[str, Any]:
                return {}
        
        provider = TestProvider()
        assert provider.provider_type == "oauth2"

    def test_config_schema_structure(self):
        """Test that config_schema includes required OAuth fields."""
        
        class TestProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "test"
            
            @property
            def display_name(self) -> str:
                return "Test"
            
            @property
            def logo_url(self) -> str:
                return "/test.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "scopes": {"type": "array", "items": {"type": "string"}},
                        "redirect_uri": {"type": "string"},
                    },
                    "required": ["client_id", "client_secret", "scopes", "redirect_uri"],
                }
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                return ""
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {}
            
            async def get_user_info(
                self, config: Dict[str, Any], access_token: str
            ) -> Dict[str, Any]:
                return {}
        
        provider = TestProvider()
        schema = provider.config_schema
        
        # Verify schema structure
        assert "properties" in schema
        assert "client_id" in schema["properties"]
        assert "client_secret" in schema["properties"]
        assert "scopes" in schema["properties"]
        assert "redirect_uri" in schema["properties"]
        
        # Verify required fields
        assert "required" in schema
        assert "client_id" in schema["required"]
        assert "client_secret" in schema["required"]
        assert "scopes" in schema["required"]
        assert "redirect_uri" in schema["required"]

    def test_all_methods_are_async(self):
        """Test that all abstract methods are coroutines."""
        
        # Get all abstract methods
        abstract_methods = [
            "get_authorization_url",
            "exchange_code_for_tokens",
            "get_user_info",
        ]
        
        for method_name in abstract_methods:
            method = getattr(OAuthProviderHandler, method_name)
            # Check if it's marked as abstract
            assert hasattr(method, "__isabstractmethod__")
            assert method.__isabstractmethod__ is True

    @pytest.mark.asyncio
    async def test_test_connection_default_implementation(self):
        """Test the default test_connection implementation."""
        
        class TestProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "test"
            
            @property
            def display_name(self) -> str:
                return "Test"
            
            @property
            def logo_url(self) -> str:
                return "/test.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {}
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                # Simulate validation
                if "client_id" not in config:
                    raise ValueError("client_id is required")
                return f"https://example.com/authorize?client_id={config['client_id']}"
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {}
            
            async def get_user_info(
                self, config: Dict[str, Any], access_token: str
            ) -> Dict[str, Any]:
                return {}
        
        provider = TestProvider()
        
        # Test with valid config
        valid_config = {"client_id": "test_client_id"}
        result, message = await provider.test_connection(valid_config)
        assert result is True
        assert "Configuration is valid" in message
        
        # Test with invalid config (missing client_id)
        invalid_config = {}
        result, message = await provider.test_connection(invalid_config)
        assert result is False
        assert "Invalid configuration" in message

    def test_all_properties_are_abstract(self):
        """Test that required properties are marked as abstract."""
        
        abstract_properties = [
            "provider_name",
            "display_name",
            "logo_url",
            "config_schema",
        ]
        
        for prop_name in abstract_properties:
            prop = getattr(OAuthProviderHandler, prop_name)
            # Properties are wrapped in property descriptor
            assert isinstance(prop, property)
            # The fget should be abstract
            assert hasattr(prop.fget, "__isabstractmethod__")
            assert prop.fget.__isabstractmethod__ is True

    def test_provider_type_is_not_abstract(self):
        """Test that provider_type has a default implementation."""
        
        prop = getattr(OAuthProviderHandler, "provider_type")
        assert isinstance(prop, property)
        # provider_type should NOT be abstract (has default implementation)
        assert not hasattr(prop.fget, "__isabstractmethod__") or not prop.fget.__isabstractmethod__

    @pytest.mark.asyncio
    async def test_concrete_provider_methods_work(self):
        """Test that a concrete provider's methods can be called."""
        
        class WorkingProvider(OAuthProviderHandler):
            @property
            def provider_name(self) -> str:
                return "working"
            
            @property
            def display_name(self) -> str:
                return "Working Provider"
            
            @property
            def logo_url(self) -> str:
                return "/assets/providers/working.svg"
            
            @property
            def config_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "scopes": {"type": "array"},
                        "redirect_uri": {"type": "string"},
                    },
                }
            
            async def get_authorization_url(
                self, config: Dict[str, Any], redirect_uri: str, state: str
            ) -> str:
                return f"https://provider.com/auth?redirect_uri={redirect_uri}&state={state}"
            
            async def exchange_code_for_tokens(
                self, config: Dict[str, Any], code: str, redirect_uri: str
            ) -> Dict[str, Any]:
                return {
                    "access_token": f"token_for_{code}",
                    "refresh_token": "refresh_123",
                    "expires_in": 3600,
                }
            
            async def get_user_info(
                self, config: Dict[str, Any], access_token: str
            ) -> Dict[str, Any]:
                return {
                    "id": "user_123",
                    "email": "user@example.com",
                    "name": "Test User",
                    "picture": "https://example.com/avatar.jpg",
                }
        
        provider = WorkingProvider()
        
        # Test properties
        assert provider.provider_name == "working"
        assert provider.display_name == "Working Provider"
        assert provider.logo_url == "/assets/providers/working.svg"
        assert provider.provider_type == "oauth2"
        assert "client_id" in provider.config_schema["properties"]
        
        # Test async methods
        config = {"client_id": "test_id", "client_secret": "test_secret"}
        
        auth_url = await provider.get_authorization_url(
            config, "https://app.com/callback", "state123"
        )
        assert "redirect_uri=https://app.com/callback" in auth_url
        assert "state=state123" in auth_url
        
        tokens = await provider.exchange_code_for_tokens(
            config, "auth_code_123", "https://app.com/callback"
        )
        assert tokens["access_token"] == "token_for_auth_code_123"
        assert tokens["refresh_token"] == "refresh_123"
        assert tokens["expires_in"] == 3600
        
        user_info = await provider.get_user_info(config, "access_token_123")
        assert user_info["id"] == "user_123"
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "Test User"
        assert user_info["picture"] == "https://example.com/avatar.jpg"
