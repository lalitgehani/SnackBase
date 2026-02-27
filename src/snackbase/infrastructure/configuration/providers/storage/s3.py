"""Amazon S3 storage provider configuration."""

from typing import Any, Dict, Optional


class S3StorageConfiguration:
    """S3 storage provider configuration definition."""

    @property
    def category(self) -> str:
        return "storage_providers"

    @property
    def provider_name(self) -> str:
        return "s3"

    @property
    def display_name(self) -> str:
        return "Amazon S3"

    @property
    def logo_url(self) -> Optional[str]:
        return "/assets/providers/aws-ses.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bucket": {
                    "type": "string",
                    "title": "Bucket",
                    "description": "S3 bucket name for file storage.",
                },
                "region": {
                    "type": "string",
                    "title": "Region",
                    "default": "us-east-1",
                    "description": "AWS region where the bucket is hosted.",
                },
                "access_key_id": {
                    "type": "string",
                    "title": "Access Key ID",
                    "description": "AWS access key ID with S3 permissions.",
                },
                "secret_access_key": {
                    "type": "string",
                    "title": "Secret Access Key",
                    "writeOnly": True,
                    "description": "AWS secret access key with S3 permissions.",
                },
                "endpoint_url": {
                    "type": "string",
                    "title": "Endpoint URL",
                    "description": (
                        "Optional custom S3-compatible endpoint URL "
                        "(for example, http://localhost:4566 for LocalStack)."
                    ),
                },
            },
            "required": ["bucket", "region", "access_key_id", "secret_access_key"],
        }

    @property
    def is_builtin(self) -> bool:
        return True
