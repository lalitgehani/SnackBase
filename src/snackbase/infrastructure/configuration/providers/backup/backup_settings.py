"""Backup settings configuration provider.

Defines the ``backup_settings`` category: where archives go (local directory or
S3), the cron schedule for automatic backups, and retention. The S3 secret is
declared with ``secret: True`` so the existing configuration encryption path
stores it as a credential.
"""

from typing import Any

from snackbase.infrastructure.backup.destinations import (
    BACKUP_SETTINGS_CATEGORY,
    BACKUP_SETTINGS_PROVIDER_NAME,
    DEFAULT_BACKUP_DIR,
)


class BackupSettingsConfiguration:
    """Backup settings configuration provider definition."""

    @property
    def category(self) -> str:
        return BACKUP_SETTINGS_CATEGORY

    @property
    def provider_name(self) -> str:
        return BACKUP_SETTINGS_PROVIDER_NAME

    @property
    def display_name(self) -> str:
        return "Backup Settings"

    @property
    def logo_url(self) -> str | None:
        return "/assets/providers/system.svg"

    @property
    def config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "title": "Destination",
                    "enum": ["local", "s3"],
                    "default": "local",
                    "description": (
                        "Where backup archives are stored. Local keeps archives "
                        "on the instance volume; S3 sends them to object storage."
                    ),
                },
                "local_path": {
                    "type": "string",
                    "title": "Local Path",
                    "default": DEFAULT_BACKUP_DIR,
                    "description": "Directory for archives when destination is local.",
                },
                "s3_bucket": {
                    "type": "string",
                    "title": "S3 Bucket",
                    "description": "Bucket for archives when destination is S3.",
                },
                "s3_region": {
                    "type": "string",
                    "title": "S3 Region",
                    "description": "AWS region of the bucket.",
                },
                "s3_access_key_id": {
                    "type": "string",
                    "title": "S3 Access Key ID",
                    "description": (
                        "AWS access key ID. Leave empty to use the environment's "
                        "credential chain (for example, an instance role)."
                    ),
                },
                "s3_secret_access_key": {
                    "type": "string",
                    "title": "S3 Secret Access Key",
                    "writeOnly": True,
                    "secret": True,
                    "description": "AWS secret access key for the archive bucket.",
                },
                "s3_key_prefix": {
                    "type": "string",
                    "title": "S3 Key Prefix",
                    "description": (
                        "Optional key prefix so archives can share a bucket "
                        "with other content."
                    ),
                },
                "s3_endpoint_url": {
                    "type": "string",
                    "title": "S3 Endpoint URL",
                    "description": (
                        "Optional custom endpoint for S3-compatible stores "
                        "(MinIO, R2, LocalStack)."
                    ),
                },
                "cron": {
                    "type": "string",
                    "title": "Schedule (cron)",
                    "default": "",
                    "description": (
                        "5-field cron expression for automatic backups. "
                        "Empty disables scheduled backups."
                    ),
                },
                "max_keep": {
                    "type": "integer",
                    "title": "Maximum Automatic Backups",
                    "default": 3,
                    "minimum": 1,
                    "description": (
                        "How many automatic (@auto_-prefixed) archives to keep. "
                        "Older ones are pruned after each scheduled backup."
                    ),
                },
            },
        }

    @property
    def is_builtin(self) -> bool:
        return True


def validate_backup_settings(values: dict[str, Any]) -> None:
    """Validate backup settings values on write.

    Rejects an invalid cron expression with the parser's message and a
    ``max_keep`` below 1 when a schedule is configured.

    Raises:
        ValueError: When a value is invalid. The message is user-presentable.
    """
    from snackbase.core.cron.parser import validate_cron

    destination = values.get("destination")
    if destination is not None and destination not in ("local", "s3"):
        raise ValueError("destination must be 'local' or 's3'")

    cron = str(values.get("cron") or "")
    if cron:
        valid, error = validate_cron(cron)
        if not valid:
            raise ValueError(error)
        try:
            max_keep = int(values.get("max_keep", 3))
        except (TypeError, ValueError):
            raise ValueError("max_keep must be an integer") from None
        if max_keep < 1:
            raise ValueError("max_keep must be at least 1 when a schedule is configured")
