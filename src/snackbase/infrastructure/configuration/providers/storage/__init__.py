"""Storage provider configuration definitions."""

from snackbase.infrastructure.configuration.providers.storage.local import (
    LocalStorageConfiguration,
)
from snackbase.infrastructure.configuration.providers.storage.s3 import (
    S3StorageConfiguration,
)

__all__ = ["LocalStorageConfiguration", "S3StorageConfiguration"]
