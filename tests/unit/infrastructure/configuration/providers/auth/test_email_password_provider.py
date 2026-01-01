"""Unit tests for EmailPasswordProvider."""

import pytest

from snackbase.infrastructure.configuration.providers.auth.email_password import (
    EmailPasswordProvider,
)


class TestEmailPasswordProvider:
    """Test suite for EmailPasswordProvider."""

    def test_provider_category(self):
        """Test provider category is auth_providers."""
        provider = EmailPasswordProvider()
        assert provider.category == "auth_providers"

    def test_provider_name(self):
        """Test provider name is email_password."""
        provider = EmailPasswordProvider()
        assert provider.provider_name == "email_password"

    def test_display_name(self):
        """Test display name is human-readable."""
        provider = EmailPasswordProvider()
        assert provider.display_name == "Email and Password"

    def test_logo_url(self):
        """Test logo_url is None (no logo for built-in provider)."""
        provider = EmailPasswordProvider()
        assert provider.logo_url is None

    def test_config_schema_is_empty(self):
        """Test config_schema is empty dict (no configuration needed)."""
        provider = EmailPasswordProvider()
        assert provider.config_schema == {}
        assert isinstance(provider.config_schema, dict)

    def test_is_builtin(self):
        """Test provider is marked as built-in."""
        provider = EmailPasswordProvider()
        assert provider.is_builtin is True

    def test_provider_instantiation(self):
        """Test provider can be instantiated without errors."""
        provider = EmailPasswordProvider()
        assert provider is not None
        assert isinstance(provider, EmailPasswordProvider)

    def test_all_properties_accessible(self):
        """Test all properties can be accessed without errors."""
        provider = EmailPasswordProvider()
        
        # Access all properties to ensure no errors
        _ = provider.category
        _ = provider.provider_name
        _ = provider.display_name
        _ = provider.logo_url
        _ = provider.config_schema
        _ = provider.is_builtin
