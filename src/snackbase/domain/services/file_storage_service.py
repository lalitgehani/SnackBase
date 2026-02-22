"""File storage service with pluggable provider support (local and S3)."""

import json
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.security.encryption import EncryptionService

logger = get_logger(__name__)
settings = get_settings()
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


@dataclass
class FileMetadata:
    """Metadata for a stored file."""

    filename: str
    size: int
    mime_type: str
    path: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "path": self.path,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, str | int]) -> "FileMetadata":
        return cls(
            filename=str(data["filename"]),
            size=int(data["size"]),
            mime_type=str(data["mime_type"]),
            path=str(data["path"]),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "FileMetadata":
        return cls.from_dict(json.loads(json_str))


class FileStorageService:
    """Service for managing file storage operations."""

    def __init__(self, storage_path: str | None = None):
        self.storage_path = Path(storage_path or settings.storage_path)
        self.encryption = EncryptionService(settings.encryption_key)

    def _generate_unique_filename(self, original_filename: str) -> str:
        suffix = Path(original_filename).suffix
        return f"{uuid.uuid4()}{suffix}"

    def validate_file_size(self, size: int) -> None:
        if size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            actual_size_mb = size / (1024 * 1024)
            raise ValueError(
                f"File size ({actual_size_mb:.2f}MB) exceeds maximum allowed "
                f"size ({max_size_mb:.2f}MB)"
            )

    def validate_mime_type(self, mime_type: str) -> None:
        if mime_type not in settings.allowed_mime_types:
            raise ValueError(
                f"File type '{mime_type}' is not allowed. "
                f"Allowed types: {', '.join(settings.allowed_mime_types)}"
            )

    async def _resolve_storage_provider(self, session: AsyncSession, account_id: str) -> tuple[str, dict]:
        account_result = await session.execute(
            select(ConfigurationModel).where(
                ConfigurationModel.category == "storage_providers",
                ConfigurationModel.account_id == account_id,
                ConfigurationModel.is_system == False,
                ConfigurationModel.enabled == True,
            )
        )
        account_configs = account_result.scalars().all()
        config_model = next((c for c in account_configs if c.is_default), None) or (account_configs[0] if account_configs else None)

        if config_model is None:
            system_result = await session.execute(
                select(ConfigurationModel).where(
                    ConfigurationModel.category == "storage_providers",
                    ConfigurationModel.account_id == SYSTEM_ACCOUNT_ID,
                    ConfigurationModel.is_system == True,
                    ConfigurationModel.enabled == True,
                )
            )
            system_configs = system_result.scalars().all()
            config_model = next((c for c in system_configs if c.is_default), None) or (system_configs[0] if system_configs else None)

        if config_model is None:
            return "local", {}

        return config_model.provider_name, self.encryption.decrypt_dict(config_model.config)

    async def save_file(
        self,
        account_id: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        size: int,
        session: AsyncSession | None = None,
    ) -> FileMetadata:
        self.validate_file_size(size)
        self.validate_mime_type(mime_type)

        if session is None:
            provider_name, provider_config = "local", {}
        else:
            provider_name, provider_config = await self._resolve_storage_provider(session, account_id)
        unique_filename = self._generate_unique_filename(filename)
        storage_key = f"{account_id}/{unique_filename}"

        if provider_name == "s3":
            self._save_s3(file_content.read(), storage_key, mime_type, provider_config)
        else:
            self._save_local(file_content.read(), storage_key)

        logger.info("File saved successfully", account_id=account_id, filename=filename, path=storage_key, provider=provider_name, size=size)
        return FileMetadata(filename=filename, size=size, mime_type=mime_type, path=storage_key)

    def _save_local(self, content: bytes, storage_key: str) -> None:
        file_path = self.storage_path / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

    def _save_s3(self, content: bytes, storage_key: str, mime_type: str, config: dict) -> None:
        s3 = boto3.client(
            "s3",
            region_name=config.get("region", "us-east-1"),
            aws_access_key_id=config.get("access_key_id"),
            aws_secret_access_key=config.get("secret_access_key"),
            endpoint_url=config.get("endpoint_url") or None,
            config=Config(s3={"addressing_style": "path" if config.get("use_path_style") else "virtual"}),
        )
        prefix = config.get("object_prefix", "").strip("/")
        object_key = f"{prefix}/{storage_key}" if prefix else storage_key
        s3.upload_fileobj(BytesIO(content), config["bucket_name"], object_key, ExtraArgs={"ContentType": mime_type})

    async def get_download_info(self, session: AsyncSession, account_id: str, file_path: str) -> tuple[str, str]:
        if session is None:
            provider_name, provider_config = "local", {}
        else:
            provider_name, provider_config = await self._resolve_storage_provider(session, account_id)
        if not file_path.startswith(f"{account_id}/"):
            raise ValueError("Access denied: file does not belong to your account")

        if provider_name == "s3":
            url = self._generate_s3_download_url(file_path, provider_config)
            return "redirect", url

        absolute_path = (self.storage_path / file_path).resolve()
        if not str(absolute_path).startswith(str(self.storage_path.resolve())):
            raise ValueError("Invalid file path")
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return "local", str(absolute_path)

    def _generate_s3_download_url(self, file_path: str, config: dict) -> str:
        s3 = boto3.client(
            "s3",
            region_name=config.get("region", "us-east-1"),
            aws_access_key_id=config.get("access_key_id"),
            aws_secret_access_key=config.get("secret_access_key"),
            endpoint_url=config.get("endpoint_url") or None,
            config=Config(s3={"addressing_style": "path" if config.get("use_path_style") else "virtual"}),
        )
        prefix = config.get("object_prefix", "").strip("/")
        object_key = f"{prefix}/{file_path}" if prefix else file_path
        expires = int(config.get("signed_url_expiry_seconds", 900))
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": config["bucket_name"], "Key": object_key},
            ExpiresIn=expires,
        )


    def get_file_path(self, account_id: str, file_path: str) -> Path:
        if not file_path.startswith(f"{account_id}/"):
            raise ValueError("Access denied: file does not belong to your account")
        absolute_path = (self.storage_path / file_path).resolve()
        if not str(absolute_path).startswith(str(self.storage_path.resolve())):
            raise ValueError("Invalid file path")
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return absolute_path

    def delete_file(self, account_id: str, file_path: str) -> None:
        absolute_path = self.get_file_path(account_id, file_path)
        absolute_path.unlink()
