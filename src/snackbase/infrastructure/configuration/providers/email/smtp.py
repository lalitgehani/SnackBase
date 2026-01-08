"""SMTP email provider configuration.

Defines the configuration schema for the SMTP email provider.
"""

from typing import Any, Dict, Optional


class SMTPConfiguration:
    """SMTP email provider configuration definition.
    
    This class defines the metadata and schema for SMTP configuration,
    allowing it to be managed via the unified configuration framework.
    """

    @property
    def category(self) -> str:
        """Provider category."""
        return "email_providers"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "smtp"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "SMTP Server"

    @property
    def logo_url(self) -> Optional[str]:
        """Path to provider logo."""
        return "/assets/providers/smtp.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        """JSON Schema for configuration validation."""
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string", 
                    "title": "SMTP Host",
                    "description": "The hostname or IP address of your SMTP server."
                },
                "port": {
                    "type": "integer", 
                    "title": "Port", 
                    "default": 587,
                    "description": "The port your SMTP server listens on (standard is 587 for TLS, 465 for SSL)."
                },
                "username": {
                    "type": "string", 
                    "title": "Username",
                    "description": "The username for SMTP authentication."
                },
                "password": {
                    "type": "string", 
                    "title": "Password", 
                    "writeOnly": True,
                    "description": "The password for SMTP authentication."
                },
                "use_tls": {
                    "type": "boolean", 
                    "title": "Use TLS", 
                    "default": True,
                    "description": "Whether to use STARTTLS (recommended for port 587)."
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "default": False,
                    "description": "Whether to use SSL/TLS connection (recommended for port 465)."
                },
                "from_email": {
                    "type": "string", 
                    "title": "From Email", 
                    "format": "email",
                    "description": "The email address that will appear in the 'From' field."
                },
                "from_name": {
                    "type": "string", 
                    "title": "From Name", 
                    "default": "SnackBase",
                    "description": "The name that will appear in the 'From' field."
                },
                "reply_to": {
                    "type": "string", 
                    "title": "Reply-To Email", 
                    "format": "email",
                    "description": "Optional email address for replies."
                }
            },
            "required": ["host", "port", "username", "password", "from_email"]
        }

    @property
    def is_builtin(self) -> bool:
        """Whether this is a built-in provider."""
        return True
