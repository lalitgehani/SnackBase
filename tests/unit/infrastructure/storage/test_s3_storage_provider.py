"""Unit tests for S3 storage provider."""

from io import BytesIO
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from snackbase.infrastructure.storage.s3_storage_provider import (
    S3StorageProvider,
    S3StorageSettings,
)


def _client_error(code: str, message: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, operation)


@pytest.fixture
def s3_provider() -> S3StorageProvider:
    return S3StorageProvider(
        S3StorageSettings(
            bucket="test-bucket",
            region="us-east-1",
            access_key_id="AKIATEST",
            secret_access_key="secret",
        )
    )


@pytest.mark.asyncio
async def test_save_file_returns_s3_prefixed_path(s3_provider: S3StorageProvider) -> None:
    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        client = mock.MagicMock()
        mock_client.return_value = client

        metadata = await s3_provider.save_file(
            account_id="acc_123",
            file_content=BytesIO(b"hello"),
            filename="hello.txt",
            mime_type="text/plain",
            size=5,
        )

    assert metadata.path.startswith("s3/acc_123/")
    assert metadata.path.endswith(".txt")
    client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_get_file_returns_content(s3_provider: S3StorageProvider) -> None:
    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        client = mock.MagicMock()
        client.get_object.return_value = {
            "Body": BytesIO(b"payload"),
            "ContentType": "text/plain",
        }
        mock_client.return_value = client

        stored_file = await s3_provider.get_file("acc_123", "s3/acc_123/file.txt")

    assert stored_file.content == b"payload"
    assert stored_file.mime_type == "text/plain"
    assert stored_file.filename == "file.txt"


@pytest.mark.asyncio
async def test_get_file_rejects_other_account_path(s3_provider: S3StorageProvider) -> None:
    with pytest.raises(ValueError, match="does not belong to this account"):
        await s3_provider.get_file("acc_123", "s3/other_account/file.txt")


@pytest.mark.asyncio
async def test_get_file_not_found_raises_file_not_found(s3_provider: S3StorageProvider) -> None:
    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        client = mock.MagicMock()
        client.get_object.side_effect = _client_error("NoSuchKey", "missing", "GetObject")
        mock_client.return_value = client

        with pytest.raises(FileNotFoundError, match="File not found"):
            await s3_provider.get_file("acc_123", "s3/acc_123/missing.txt")


@pytest.mark.asyncio
async def test_test_connection_success(s3_provider: S3StorageProvider) -> None:
    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        client = mock.MagicMock()
        mock_client.return_value = client

        success, message = await s3_provider.test_connection()

    assert success is True
    assert message is not None
    assert "test-bucket" in message
    client.head_bucket.assert_called_once_with(Bucket="test-bucket")


def test_get_client_passes_endpoint_url_when_configured() -> None:
    provider = S3StorageProvider(
        S3StorageSettings(
            bucket="test-bucket",
            region="us-east-1",
            access_key_id="AKIATEST",
            secret_access_key="secret",
            endpoint_url="http://localhost:4566",
        )
    )

    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        provider._get_client()

    mock_client.assert_called_once_with(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="AKIATEST",
        aws_secret_access_key="secret",
        endpoint_url="http://localhost:4566",
    )


def test_get_client_omits_endpoint_url_when_not_configured() -> None:
    provider = S3StorageProvider(
        S3StorageSettings(
            bucket="test-bucket",
            region="us-east-1",
            access_key_id="AKIATEST",
            secret_access_key="secret",
        )
    )

    with mock.patch("snackbase.infrastructure.storage.s3_storage_provider.boto3.client") as mock_client:
        provider._get_client()

    _args, kwargs = mock_client.call_args
    assert "endpoint_url" not in kwargs
