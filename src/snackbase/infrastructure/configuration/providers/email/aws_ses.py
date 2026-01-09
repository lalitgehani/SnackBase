"""AWS SES email provider configuration.

Defines the configuration schema for the AWS SES email provider.
"""

from typing import Any, Dict, Optional


class AWSESConfiguration:
    """AWS SES email provider configuration definition.
    
    This class defines the metadata and schema for AWS SES configuration,
    allowing it to be managed via the unified configuration framework.
    """

    @property
    def category(self) -> str:
        """Provider category."""
        return "email_providers"

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "aws_ses"

    @property
    def display_name(self) -> str:
        """Human-readable provider name."""
        return "AWS SES"

    @property
    def logo_url(self) -> Optional[str]:
        """Path to provider logo."""
        return "/assets/providers/aws-ses.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        """JSON Schema for configuration validation."""
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "title": "AWS Region",
                    "default": "us-east-1",
                    "description": "The AWS region where your SES service is configured.",
                },
                "access_key_id": {
                    "type": "string",
                    "title": "Access Key ID",
                    "description": "Your AWS IAM access key ID with SES permissions.",
                },
                "secret_access_key": {
                    "type": "string",
                    "title": "Secret Access Key",
                    "writeOnly": True,
                    "description": "Your AWS IAM secret access key.",
                },
                "from_email": {
                    "type": "string",
                    "title": "From Email",
                    "format": "email",
                    "description": (
                        "The email address that will appear in the 'From' field. "
                        "Must be verified in AWS SES."
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
            "required": ["region", "access_key_id", "secret_access_key", "from_email"],
        }

    @property
    def is_builtin(self) -> bool:
        """Whether this is a built-in provider."""
        return True
