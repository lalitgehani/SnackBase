"""System configuration provider.

Defines the configuration schema for global system settings like app name,
app URL, and support email.
"""

from typing import Any


class SystemConfiguration:
    """System configuration provider definition.

    This class defines the metadata and schema for system-wide configuration,
    allowing global settings to be managed via the unified configuration framework.
    """

    @property
    def category(self) -> str:
        """Provider category."""
        return "system_settings"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "system"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "System Settings"

    @property
    def logo_url(self) -> str | None:
        """Path to provider logo."""
        return "/assets/providers/system.svg"

    @property
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for configuration validation."""
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "title": "Application Name",
                    "default": "SnackBase",
                    "description": "The name of your application, used in emails and UI.",
                },
                "app_url": {
                    "type": "string",
                    "title": "Application URL",
                    "format": "uri",
                    "description": "The base URL of your application (e.g., https://example.com).",
                },
                "support_email": {
                    "type": "string",
                    "title": "Support Email",
                    "format": "email",
                    "description": "Contact email for user support and system notifications.",
                },
            },
            "required": ["app_name", "app_url"],
        }

    @property
    def is_builtin(self) -> bool:
        """Whether this is a built-in provider."""
        return True
