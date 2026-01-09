"""Resend email provider configuration.

Defines the configuration schema for the Resend email provider.
"""

from typing import Any


class ResendConfiguration:
    """Resend email provider configuration definition.

    This class defines the metadata and schema for Resend configuration,
    allowing it to be managed via the unified configuration framework.
    """

    @property
    def category(self) -> str:
        """Provider category."""
        return "email_providers"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "resend"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "Resend"

    @property
    def logo_url(self) -> str | None:
        """Path to provider logo."""
        return "/assets/providers/resend.svg"

    @property
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for configuration validation."""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "writeOnly": True,
                    "description": "Your Resend API key from the Resend dashboard.",
                },
                "from_email": {
                    "type": "string",
                    "title": "From Email",
                    "format": "email",
                    "description": (
                        "The email address that will appear in the 'From' field. "
                        "Must be from a verified domain in Resend."
                    ),
                },
                "from_name": {
                    "type": "string",
                    "title": "From Name",
                    "default": "SnackBase",
                    "description": "The name that will appear in the 'From' field.",
                },
                "reply_to": {
                    "type": "string",
                    "title": "Reply-To Email",
                    "format": "email",
                    "description": "Optional email address for replies.",
                },
            },
            "required": ["api_key", "from_email"],
        }

    @property
    def is_builtin(self) -> bool:
        """Whether this is a built-in provider."""
        return True
