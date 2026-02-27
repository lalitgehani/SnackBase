"""Local storage provider configuration."""

from typing import Any, Dict, Optional


class LocalStorageConfiguration:
    """Built-in local filesystem storage provider configuration definition."""

    @property
    def category(self) -> str:
        return "storage_providers"

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def display_name(self) -> str:
        return "Local Filesystem"

    @property
    def logo_url(self) -> Optional[str]:
        return "/assets/providers/system.svg"

    @property
    def config_schema(self) -> Dict[str, Any]:
        # Local filesystem provider uses app-level storage path settings.
        return {}

    @property
    def is_builtin(self) -> bool:
        return True
