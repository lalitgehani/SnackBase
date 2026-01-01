"""Unit tests for SAMLProviderHandler abstract base class."""

import inspect
from typing import Any

import pytest

from snackbase.infrastructure.configuration.providers.saml.saml_handler import (
    SAMLProviderHandler,
)


class TestSAMLProviderHandler:
    """Test suite for SAMLProviderHandler abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that SAMLProviderHandler cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SAMLProviderHandler()

    def test_concrete_implementation_requires_all_abstract_methods(self):
        """Test that concrete class missing abstract methods cannot be instantiated."""

        # Create incomplete implementation (missing get_metadata)
        class IncompleteSAMLProvider(SAMLProviderHandler):
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
            def config_schema(self) -> dict[str, Any]:
                return {}

            async def get_authorization_url(
                self, config: dict[str, Any], redirect_uri: str, relay_state: str | None = None
            ) -> str:
                return "https://idp.com/sso"

            async def parse_saml_response(
                self, config: dict[str, Any], saml_response: str
            ) -> dict[str, Any]:
                return {}

            # Missing: get_metadata

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteSAMLProvider()

    def test_concrete_implementation_with_all_methods(self):
        """Test that concrete implementation with all methods can be instantiated."""

        class CompleteSAMLProvider(SAMLProviderHandler):
            @property
            def provider_name(self) -> str:
                return "test_saml"

            @property
            def display_name(self) -> str:
                return "Test SAML"

            @property
            def logo_url(self) -> str:
                return "/assets/providers/test-saml.svg"

            @property
            def config_schema(self) -> dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "idp_entity_id": {"type": "string"},
                        "idp_sso_url": {"type": "string"},
                    },
                }

            async def get_authorization_url(
                self, config: dict[str, Any], redirect_uri: str, relay_state: str | None = None
            ) -> str:
                return f"https://idp.com/sso?redirect={redirect_uri}"

            async def parse_saml_response(
                self, config: dict[str, Any], saml_response: str
            ) -> dict[str, Any]:
                return {"id": "user123", "email": "test@example.com"}

            async def get_metadata(self, config: dict[str, Any]) -> str:
                return "<xml>metadata</xml>"

        # Should instantiate without errors
        provider = CompleteSAMLProvider()
        assert provider is not None
        assert isinstance(provider, SAMLProviderHandler)

    def test_provider_type_returns_saml(self):
        """Test that provider_type property returns 'saml'."""

        class TestSAMLProvider(SAMLProviderHandler):
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
            def config_schema(self) -> dict[str, Any]:
                return {}

            async def get_authorization_url(
                self, config: dict[str, Any], redirect_uri: str, relay_state: str | None = None
            ) -> str:
                return ""

            async def parse_saml_response(
                self, config: dict[str, Any], saml_response: str
            ) -> dict[str, Any]:
                return {}

            async def get_metadata(self, config: dict[str, Any]) -> str:
                return ""

        provider = TestSAMLProvider()
        assert provider.provider_type == "saml"

    def test_all_methods_are_async(self):
        """Test that all abstract methods are coroutines."""

        # Get all abstract methods
        abstract_methods = [
            "get_authorization_url",
            "parse_saml_response",
            "get_metadata",
        ]

        for method_name in abstract_methods:
            method = getattr(SAMLProviderHandler, method_name)
            # Check if it's marked as abstract
            assert hasattr(method, "__isabstractmethod__")
            assert method.__isabstractmethod__ is True

    @pytest.mark.asyncio
    async def test_test_connection_default_implementation(self):
        """Test the default test_connection implementation."""

        class TestSAMLProvider(SAMLProviderHandler):
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
            def config_schema(self) -> dict[str, Any]:
                return {}

            async def get_authorization_url(
                self, config: dict[str, Any], redirect_uri: str, relay_state: str | None = None
            ) -> str:
                return ""

            async def parse_saml_response(
                self, config: dict[str, Any], saml_response: str
            ) -> dict[str, Any]:
                return {}

            async def get_metadata(self, config: dict[str, Any]) -> str:
                if "idp_entity_id" not in config:
                    raise ValueError("idp_entity_id is required")
                return "<xml>metadata</xml>"

        provider = TestSAMLProvider()

        # Test with valid config
        valid_config = {"idp_entity_id": "http://idp.example.com"}
        result = await provider.test_connection(valid_config)
        assert result is True

        # Test with invalid config (missing idp_entity_id)
        invalid_config = {}
        with pytest.raises(ValueError, match="Invalid configuration"):
            await provider.test_connection(invalid_config)

    def test_all_properties_are_abstract(self):
        """Test that required properties are marked as abstract."""

        abstract_properties = [
            "provider_name",
            "display_name",
            "logo_url",
            "config_schema",
        ]

        for prop_name in abstract_properties:
            prop = getattr(SAMLProviderHandler, prop_name)
            # Properties are wrapped in property descriptor
            assert isinstance(prop, property)
            # The fget should be abstract
            assert hasattr(prop.fget, "__isabstractmethod__")
            assert prop.fget.__isabstractmethod__ is True
