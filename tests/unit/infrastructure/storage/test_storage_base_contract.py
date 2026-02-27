"""Tests for storage provider base contract."""

from pathlib import Path

import pytest

from snackbase.infrastructure.storage.base import StorageProvider
from snackbase.infrastructure.storage.local_storage_provider import LocalStorageProvider


def test_storage_provider_is_abstract() -> None:
    """StorageProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        StorageProvider()  # type: ignore[abstract]


def test_local_provider_implements_storage_provider(tmp_path: Path) -> None:
    """Local provider should implement the storage provider contract."""
    provider = LocalStorageProvider(storage_path=str(tmp_path))
    assert isinstance(provider, StorageProvider)
