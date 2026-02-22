"""Amazon S3 storage provider configuration."""

from typing import Any, Dict, Optional


class S3StorageConfiguration:
    """Amazon S3 storage provider configuration definition."""

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
        return "/assets/providers/aws-s3.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bucket_name": {
                    "type": "string",
                    "title": "S3 Bucket Name",
                    "description": "Name of the S3 bucket used to store files.",
                },
                "region": {
                    "type": "string",
                    "title": "AWS Region",
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
                    "description": "AWS secret access key.",
                },
                "endpoint_url": {
                    "type": "string",
                    "title": "Endpoint URL",
                    "description": "Optional custom S3 endpoint (useful for S3-compatible providers).",
                },
                "object_prefix": {
                    "type": "string",
                    "title": "Object Prefix",
                    "default": "",
                    "description": "Optional prefix/folder inside the bucket.",
                },
                "use_path_style": {
                    "type": "boolean",
                    "title": "Use Path-Style URLs",
                    "default": False,
                    "description": "Enable for providers requiring path-style addressing.",
                },
            },
            "required": ["bucket_name", "region", "access_key_id", "secret_access_key"],
        }

    @property
    def is_builtin(self) -> bool:
        return True
