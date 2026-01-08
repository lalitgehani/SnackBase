"""Unit tests for SystemConfiguration provider."""

import pytest

from snackbase.infrastructure.configuration.providers.system import SystemConfiguration


class TestSystemConfiguration:
    """Test suite for SystemConfiguration provider."""

    def test_category(self):
        """Test that category is 'system_settings'."""
        config = SystemConfiguration()
        assert config.category == "system_settings"

    def test_provider_name(self):
        """Test that provider_name is 'system'."""
        config = SystemConfiguration()
        assert config.provider_name == "system"

    def test_display_name(self):
        """Test that display_name is 'System Settings'."""
        config = SystemConfiguration()
        assert config.display_name == "System Settings"

    def test_logo_url(self):
        """Test that logo_url is correct."""
        config = SystemConfiguration()
        assert config.logo_url == "/assets/providers/system.svg"

    def test_is_builtin(self):
        """Test that is_builtin is True."""
        config = SystemConfiguration()
        assert config.is_builtin is True

    def test_config_schema_structure(self):
        """Test that config_schema has correct structure."""
        config = SystemConfiguration()
        schema = config.config_schema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_config_schema_properties(self):
        """Test that config_schema has all required properties."""
        config = SystemConfiguration()
        schema = config.config_schema
        properties = schema["properties"]

        # Check app_name
        assert "app_name" in properties
        assert properties["app_name"]["type"] == "string"
        assert properties["app_name"]["title"] == "Application Name"
        assert properties["app_name"]["default"] == "SnackBase"

        # Check app_url
        assert "app_url" in properties
        assert properties["app_url"]["type"] == "string"
        assert properties["app_url"]["title"] == "Application URL"
        assert properties["app_url"]["format"] == "uri"

        # Check support_email
        assert "support_email" in properties
        assert properties["support_email"]["type"] == "string"
        assert properties["support_email"]["title"] == "Support Email"
        assert properties["support_email"]["format"] == "email"

    def test_config_schema_required_fields(self):
        """Test that config_schema has correct required fields."""
        config = SystemConfiguration()
        schema = config.config_schema

        assert "app_name" in schema["required"]
        assert "app_url" in schema["required"]
        # support_email is optional
        assert "support_email" not in schema["required"]

    def test_config_schema_descriptions(self):
        """Test that all properties have descriptions."""
        config = SystemConfiguration()
        schema = config.config_schema
        properties = schema["properties"]

        for prop_name, prop_schema in properties.items():
            assert "description" in prop_schema, f"{prop_name} missing description"
            assert len(prop_schema["description"]) > 0, f"{prop_name} has empty description"
