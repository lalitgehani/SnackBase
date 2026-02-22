"""Local filesystem storage provider configuration."""

from typing import Any, Dict, Optional


class LocalStorageConfiguration:
    """Built-in local filesystem storage provider."""

    @property
    def category(self) -> str:
        return "storage_providers"

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def display_name(self) -> str:
        return "Local File Storage"

    @property
    def logo_url(self) -> Optional[str]:
        return "/assets/providers/storage-local.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {}

    @property
    def is_builtin(self) -> bool:
        return True

