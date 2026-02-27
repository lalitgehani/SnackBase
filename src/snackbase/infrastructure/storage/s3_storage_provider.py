"""Amazon S3 storage provider."""

import asyncio
import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict

from snackbase.core.config import get_settings
from snackbase.domain.services.file_storage_service import FileMetadata
from snackbase.infrastructure.storage.base import StoredFile, StorageProvider

S3_PREFIX = "s3/"


class S3StorageSettings(BaseModel):
    """Configuration settings for the S3 storage provider."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: str | None = None


class S3StorageProvider(StorageProvider):
    """Storage provider implementation for Amazon S3."""

    def __init__(self, settings: S3StorageSettings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self):
        """Get or create the S3 client."""
        if self._client is None:
            client_kwargs = {
                "region_name": self.settings.region,
                "aws_access_key_id": self.settings.access_key_id,
                "aws_secret_access_key": self.settings.secret_access_key,
            }
            if self.settings.endpoint_url:
                client_kwargs["endpoint_url"] = self.settings.endpoint_url

            self._client = boto3.client("s3", **client_kwargs)
        return self._client

    @staticmethod
    def _generate_unique_filename(original_filename: str) -> str:
        suffix = Path(original_filename).suffix
        return f"{uuid.uuid4()}{suffix}"

    @staticmethod
    def _key_to_path(key: str) -> str:
        return f"{S3_PREFIX}{key}"

    @staticmethod
    def _path_to_key(account_id: str, file_path: str) -> str:
        if not file_path.startswith(S3_PREFIX):
            raise ValueError("Invalid S3 file path format")

        key = file_path[len(S3_PREFIX) :]
        if not key.startswith(f"{account_id}/"):
            raise ValueError("Invalid file path: does not belong to this account")
        return key

    @staticmethod
    def _validate_file_size(size: int) -> None:
        settings = get_settings()
        if size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            actual_size_mb = size / (1024 * 1024)
            raise ValueError(
                f"File size ({actual_size_mb:.2f}MB) exceeds maximum allowed "
                f"size ({max_size_mb:.2f}MB)"
            )

    @staticmethod
    def _validate_mime_type(mime_type: str) -> None:
        settings = get_settings()
        if mime_type not in settings.allowed_mime_types:
            raise ValueError(
                f"File type '{mime_type}' is not allowed. "
                f"Allowed types: {', '.join(settings.allowed_mime_types)}"
            )

    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
    ) -> FileMetadata:
        self._validate_file_size(size)
        self._validate_mime_type(mime_type)

        unique_filename = self._generate_unique_filename(filename)
        key = f"{account_id}/{unique_filename}"
        body = file_content.read()

        try:
            await asyncio.to_thread(
                self._get_client().put_object,
                Bucket=self.settings.bucket,
                Key=key,
                Body=body,
                ContentType=mime_type,
            )
        except (ClientError, BotoCoreError) as e:
            raise RuntimeError(f"Failed to upload file to S3: {str(e)}") from e

        return FileMetadata(
            filename=filename,
            size=size,
            mime_type=mime_type,
            path=self._key_to_path(key),
        )

    async def get_file(self, account_id: str, file_path: str) -> StoredFile:
        key = self._path_to_key(account_id, file_path)

        try:
            response = await asyncio.to_thread(
                self._get_client().get_object,
                Bucket=self.settings.bucket,
                Key=key,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(f"File not found: {file_path}") from e
            raise RuntimeError(f"Failed to fetch file from S3: {str(e)}") from e
        except BotoCoreError as e:
            raise RuntimeError(f"Failed to fetch file from S3: {str(e)}") from e

        body_stream = response.get("Body")
        if body_stream is None:
            raise FileNotFoundError(f"File not found: {file_path}")

        content = await asyncio.to_thread(body_stream.read)
        return StoredFile(
            content=content,
            filename=Path(key).name,
            mime_type=response.get("ContentType", "application/octet-stream"),
        )

    async def delete_file(self, account_id: str, file_path: str) -> None:
        key = self._path_to_key(account_id, file_path)

        try:
            await asyncio.to_thread(
                self._get_client().head_object,
                Bucket=self.settings.bucket,
                Key=key,
            )
            await asyncio.to_thread(
                self._get_client().delete_object,
                Bucket=self.settings.bucket,
                Key=key,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError(f"File not found: {file_path}") from e
            raise RuntimeError(f"Failed to delete file from S3: {str(e)}") from e
        except BotoCoreError as e:
            raise RuntimeError(f"Failed to delete file from S3: {str(e)}") from e

    async def test_connection(self) -> tuple[bool, str | None]:
        try:
            await asyncio.to_thread(self._get_client().head_bucket, Bucket=self.settings.bucket)
            return True, (
                f"S3 connection successful. Bucket '{self.settings.bucket}' "
                f"is accessible in region '{self.settings.region}'."
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            return False, f"S3 connection failed ({error_code}): {error_message}"
        except BotoCoreError as e:
            return False, f"S3 connection failed: {str(e)}"
        except Exception as e:
            return False, f"S3 connection failed: {str(e)}"
