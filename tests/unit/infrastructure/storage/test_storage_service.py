"""Unit tests for storage service provider resolution."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.file_storage_service import FileMetadata
from snackbase.infrastructure.security.encryption import EncryptionService
from snackbase.infrastructure.storage.base import StoredFile
from snackbase.infrastructure.storage.storage_service import StorageService


@pytest.fixture
def mock_session() -> AsyncSession:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def storage_service(mock_session: AsyncSession) -> StorageService:
    return StorageService(
        session=mock_session,
        encryption_service=EncryptionService("test-key-must-be-32-bytes-long!!!!"),
    )


@pytest.mark.asyncio
async def test_save_file_falls_back_to_local_when_no_configs(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_service._config_repo, "list_configs", AsyncMock(return_value=[]))

    expected = FileMetadata(
        filename="test.txt",
        size=4,
        mime_type="text/plain",
        path="acc_1/test.txt",
    )
    local_save = AsyncMock(return_value=expected)
    monkeypatch.setattr(storage_service._local_provider, "save_file", local_save)

    metadata = await storage_service.save_file(
        account_id="acc_1",
        file_content=BytesIO(b"test"),
        filename="test.txt",
        mime_type="text/plain",
        size=4,
    )

    assert metadata == expected
    local_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_file_uses_default_provider(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encrypted_s3 = storage_service._encryption_service.encrypt_dict(
        {
            "bucket": "bucket",
            "region": "us-east-1",
            "access_key_id": "key",
            "secret_access_key": "secret",
        }
    )
    configs = [
        SimpleNamespace(provider_name="local", config={}, is_default=False),
        SimpleNamespace(provider_name="s3", config=encrypted_s3, is_default=True),
    ]
    monkeypatch.setattr(storage_service._config_repo, "list_configs", AsyncMock(return_value=configs))

    selected_provider = {"name": None}
    expected = FileMetadata(
        filename="test.txt",
        size=4,
        mime_type="text/plain",
        path="s3/acc_1/test.txt",
    )

    class DummyProvider:
        async def save_file(self, **_: object) -> FileMetadata:
            return expected

    def fake_provider_from_config(
        provider_name: str, encrypted_config: dict[str, object]
    ) -> DummyProvider:
        del encrypted_config
        selected_provider["name"] = provider_name
        return DummyProvider()

    monkeypatch.setattr(storage_service, "_provider_from_config", fake_provider_from_config)

    metadata = await storage_service.save_file(
        account_id="acc_1",
        file_content=BytesIO(b"test"),
        filename="test.txt",
        mime_type="text/plain",
        size=4,
    )

    assert selected_provider["name"] == "s3"
    assert metadata == expected


@pytest.mark.asyncio
async def test_get_file_routes_local_paths_to_local_provider(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = StoredFile(local_path=None, content=b"local")
    local_get = AsyncMock(return_value=expected)
    monkeypatch.setattr(storage_service._local_provider, "get_file", local_get)

    result = await storage_service.get_file("acc_1", "acc_1/file.txt")

    assert result == expected
    local_get.assert_awaited_once_with(account_id="acc_1", file_path="acc_1/file.txt")


@pytest.mark.asyncio
async def test_get_file_routes_s3_paths_to_s3_provider(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = StoredFile(content=b"s3-data")
    s3_provider = SimpleNamespace(get_file=AsyncMock(return_value=expected))
    monkeypatch.setattr(storage_service, "_get_s3_provider", AsyncMock(return_value=s3_provider))

    result = await storage_service.get_file("acc_1", "s3/acc_1/file.txt")

    assert result == expected
    s3_provider.get_file.assert_awaited_once_with(
        account_id="acc_1",
        file_path="s3/acc_1/file.txt",
    )


@pytest.mark.asyncio
async def test_get_s3_provider_requires_enabled_system_config(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_service._config_repo, "get_config", AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="not configured or enabled"):
        await storage_service._get_s3_provider()


@pytest.mark.asyncio
async def test_save_file_raises_when_system_configs_exist_but_none_enabled(
    storage_service: StorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        storage_service._config_repo,
        "list_configs",
        AsyncMock(side_effect=[[], [SimpleNamespace(provider_name="local", enabled=False)]]),
    )

    with pytest.raises(ValueError, match="No enabled system storage provider configured"):
        await storage_service.save_file(
            account_id="acc_1",
            file_content=BytesIO(b"test"),
            filename="test.txt",
            mime_type="text/plain",
            size=4,
        )
