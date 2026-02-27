"""Integration tests for file storage functionality."""

import json
import uuid
from io import BytesIO
from unittest import mock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel
from snackbase.infrastructure.security.encryption import EncryptionService


@pytest.mark.asyncio
async def test_create_collection_with_file_field(client: AsyncClient, superadmin_token: str):
    """Test creating a collection with a file field type."""
    response = await client.post(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "name": "documents",
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "attachment", "type": "file", "required": False},
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "documents"
    assert len(data["schema"]) == 2
    
    # Find the file field
    file_field = next(f for f in data["schema"] if f["name"] == "attachment")
    assert file_field["type"] == "file"
    assert file_field["required"] is False


@pytest.mark.asyncio
async def test_upload_file_requires_authentication(client: AsyncClient):
    """Test that file upload requires authentication."""
    # Create a test file
    file_content = b"test content"
    files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

    response = await client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_and_download_file(client: AsyncClient, superadmin_token: str):
    """Test uploading a file and downloading it."""
    # Upload a file
    file_content = b"test content for file storage"
    files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )

    assert upload_response.status_code == 201
    upload_data = upload_response.json()
    
    assert upload_data["success"] is True
    assert upload_data["file"]["filename"] == "test.txt"
    assert upload_data["file"]["size"] == len(file_content)
    assert upload_data["file"]["mime_type"] == "text/plain"
    assert upload_data["file"]["path"].startswith("00000000-0000-0000-0000-000000000000/")

    # Download the file
    file_path = upload_data["file"]["path"]
    download_response = await client.get(
        f"/api/v1/files/{file_path}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )

    assert download_response.status_code == 200
    assert download_response.content == file_content


@pytest.mark.asyncio
async def test_upload_file_size_limit(client: AsyncClient, superadmin_token: str):
    """Test that file upload enforces size limit."""
    # Create a file that exceeds the limit (default 10MB)
    # We'll create a 11MB file
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large.txt", BytesIO(large_content), "text/plain")}

    response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )

    assert response.status_code == 400
    assert "exceeds maximum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_mime_type(client: AsyncClient, superadmin_token: str):
    """Test that file upload rejects disallowed MIME types."""
    # Try to upload an executable file (not in allowed types)
    file_content = b"fake executable"
    files = {"file": ("test.exe", BytesIO(file_content), "application/x-executable")}

    response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_record_with_file_field(
    client: AsyncClient, superadmin_token: str, db_session: AsyncSession
):
    """Test creating a record with file metadata."""
    # First create a collection with a file field
    collection_response = await client.post(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "name": "documents",
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "attachment", "type": "file", "required": False},
            ],
        },
    )
    assert collection_response.status_code == 201

    # Upload a file
    file_content = b"document content"
    files = {"file": ("document.pdf", BytesIO(file_content), "application/pdf")}

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )
    assert upload_response.status_code == 201
    file_metadata = upload_response.json()["file"]

    # Create a record with the file metadata
    record_response = await client.post(
        "/api/v1/records/documents",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "title": "Important Document",
            "attachment": file_metadata,
        },
    )

    assert record_response.status_code == 201
    record_data = record_response.json()
    assert record_data["title"] == "Important Document"
    
    # The attachment field should contain the file metadata
    attachment = record_data["attachment"]
    if isinstance(attachment, str):
        attachment = json.loads(attachment)
    
    assert attachment["filename"] == "document.pdf"
    assert attachment["size"] == len(file_content)
    assert attachment["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_file_requires_authentication(client: AsyncClient, superadmin_token: str):
    """Test that file download requires authentication."""
    # Upload a file first
    file_content = b"test content"
    files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )
    assert upload_response.status_code == 201
    file_path = upload_response.json()["file"]["path"]

    # Try to download without authentication
    response = await client.get(f"/api/v1/files/{file_path}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_file_wrong_account(
    client: AsyncClient, superadmin_token: str, regular_user_token: str
):
    """Test that users cannot download files from other accounts."""
    # Superadmin uploads a file
    file_content = b"superadmin file"
    files = {"file": ("admin.txt", BytesIO(file_content), "text/plain")}

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        files=files,
    )
    assert upload_response.status_code == 201
    file_path = upload_response.json()["file"]["path"]

    # Regular user tries to download (different account)
    response = await client.get(
        f"/api/v1/files/{file_path}",
        headers={"Authorization": f"Bearer {regular_user_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_file_field_validation_invalid_metadata(
    client: AsyncClient, superadmin_token: str
):
    """Test that file field validation rejects invalid metadata."""
    # Create a collection with a file field
    collection_response = await client.post(
        "/api/v1/collections",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "name": "documents",
            "schema": [
                {"name": "title", "type": "text", "required": True},
                {"name": "attachment", "type": "file", "required": False},
            ],
        },
    )
    assert collection_response.status_code == 201

    # Try to create a record with invalid file metadata (missing required fields)
    record_response = await client.post(
        "/api/v1/records/documents",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "title": "Document",
            "attachment": {"filename": "test.txt"},  # Missing size, mime_type, path
        },
    )

    assert record_response.status_code == 400
    response_data = record_response.json()
    # Check that validation error is present in details field
    assert "details" in response_data
    assert any("missing required fields" in err["message"].lower() for err in response_data["details"])


@pytest.mark.asyncio
async def test_upload_and_download_file_with_s3_default(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token: str,
):
    """Test upload/download flow when S3 is configured as system default provider."""
    system_account_id = "00000000-0000-0000-0000-000000000000"
    settings = get_settings()
    encryption_service = EncryptionService(settings.encryption_key)

    # Clear existing storage defaults so S3 can be set as default.
    existing_storage_configs_result = await db_session.execute(
        select(ConfigurationModel).where(
            ConfigurationModel.category == "storage_providers",
            ConfigurationModel.account_id == system_account_id,
            ConfigurationModel.is_system == True,  # noqa: E712
        )
    )
    for config_model in existing_storage_configs_result.scalars().all():
        config_model.is_default = False

    s3_config_result = await db_session.execute(
        select(ConfigurationModel).where(
            ConfigurationModel.category == "storage_providers",
            ConfigurationModel.account_id == system_account_id,
            ConfigurationModel.provider_name == "s3",
            ConfigurationModel.is_system == True,  # noqa: E712
        )
    )
    s3_config = s3_config_result.scalar_one_or_none()
    encrypted_config = encryption_service.encrypt_dict(
        {
            "bucket": "test-bucket",
            "region": "us-east-1",
            "access_key_id": "AKIATEST",
            "secret_access_key": "secret",
        }
    )
    if s3_config is None:
        s3_config = ConfigurationModel(
            id=str(uuid.uuid4()),
            account_id=system_account_id,
            category="storage_providers",
            provider_name="s3",
            display_name="Amazon S3",
            config=encrypted_config,
            enabled=True,
            is_system=True,
            is_default=True,
        )
        db_session.add(s3_config)
    else:
        s3_config.config = encrypted_config
        s3_config.enabled = True
        s3_config.is_default = True

    await db_session.commit()

    stored_objects: dict[tuple[str, str], tuple[bytes, str]] = {}

    class FakeS3Client:
        def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
            stored_objects[(Bucket, Key)] = (Body, ContentType)

        def get_object(self, Bucket: str, Key: str) -> dict:
            if (Bucket, Key) not in stored_objects:
                from botocore.exceptions import ClientError

                raise ClientError(
                    {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
                    "GetObject",
                )

            payload, content_type = stored_objects[(Bucket, Key)]
            return {"Body": BytesIO(payload), "ContentType": content_type}

        def head_bucket(self, Bucket: str) -> None:
            del Bucket

    fake_client = FakeS3Client()

    with mock.patch(
        "snackbase.infrastructure.storage.s3_storage_provider.boto3.client",
        return_value=fake_client,
    ):
        file_content = b"s3 file content"
        files = {"file": ("cloud.txt", BytesIO(file_content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/files/upload",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            files=files,
        )

        assert upload_response.status_code == 201
        uploaded_path = upload_response.json()["file"]["path"]
        assert uploaded_path.startswith("s3/00000000-0000-0000-0000-000000000000/")

        download_response = await client.get(
            f"/api/v1/files/{uploaded_path}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert download_response.status_code == 200
        assert download_response.content == file_content
