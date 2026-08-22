"""Email/Password authentication provider.

This module defines the built-in email/password authentication provider
that integrates with the unified configuration framework.
"""

from typing import Any


class EmailPasswordProvider:
    """Built-in email/password authentication provider.

    This provider represents the traditional email/password authentication
    method. It requires no configuration as the authentication logic is
    built into the core authentication system.
    """

    @property
    def category(self) -> str:
        """Provider category."""
        return "auth_providers"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "email_password"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "Email and Password"

    @property
    def logo_url(self) -> str | None:
        """Path to provider logo."""
        return "/assets/providers/email.svg"

    @property
    def config_schema(self) -> dict[str, Any]:
        """JSON Schema for configuration validation.

        Email/password authentication requires no configuration,
        so the schema is an empty object.
        """
        return {}

    @property
    def is_builtin(self) -> bool:
        """Whether this is a built-in provider that cannot be deleted."""
        return True
