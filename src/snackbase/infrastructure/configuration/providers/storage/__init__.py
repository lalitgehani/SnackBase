"""Storage provider configuration implementations."""

from snackbase.infrastructure.configuration.providers.storage.aws_s3 import (
    S3StorageConfiguration,
)
from snackbase.infrastructure.configuration.providers.storage.local import (
    LocalStorageConfiguration,
)

__all__ = ["LocalStorageConfiguration", "S3StorageConfiguration"]
