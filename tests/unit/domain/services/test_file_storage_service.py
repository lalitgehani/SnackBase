"""Unit tests for file storage service."""

import json
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

from snackbase.domain.services.file_storage_service import FileMetadata, FileStorageService


class TestFileMetadata:
    """Tests for FileMetadata dataclass."""

    def test_to_dict(self):
        """Test converting FileMetadata to dictionary."""
        metadata = FileMetadata(
            filename="test.txt",
            size=1024,
            mime_type="text/plain",
            path="account123/uuid-test.txt",
        )

        result = metadata.to_dict()

        assert result == {
            "filename": "test.txt",
            "size": 1024,
            "mime_type": "text/plain",
            "path": "account123/uuid-test.txt",
        }

    def test_to_json(self):
        """Test converting FileMetadata to JSON string."""
        metadata = FileMetadata(
            filename="test.txt",
            size=1024,
            mime_type="text/plain",
            path="account123/uuid-test.txt",
        )

        result = metadata.to_json()
        parsed = json.loads(result)

        assert parsed["filename"] == "test.txt"
        assert parsed["size"] == 1024
        assert parsed["mime_type"] == "text/plain"
        assert parsed["path"] == "account123/uuid-test.txt"

    def test_from_dict(self):
        """Test creating FileMetadata from dictionary."""
        data = {
            "filename": "test.txt",
            "size": 1024,
            "mime_type": "text/plain",
            "path": "account123/uuid-test.txt",
        }

        metadata = FileMetadata.from_dict(data)

        assert metadata.filename == "test.txt"
        assert metadata.size == 1024
        assert metadata.mime_type == "text/plain"
        assert metadata.path == "account123/uuid-test.txt"

    def test_from_json(self):
        """Test creating FileMetadata from JSON string."""
        json_str = json.dumps({
            "filename": "test.txt",
            "size": 1024,
            "mime_type": "text/plain",
            "path": "account123/uuid-test.txt",
        })

        metadata = FileMetadata.from_json(json_str)

        assert metadata.filename == "test.txt"
        assert metadata.size == 1024
        assert metadata.mime_type == "text/plain"
        assert metadata.path == "account123/uuid-test.txt"


class TestFileStorageService:
    """Tests for FileStorageService."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage_service(self, temp_storage_path):
        """Create a FileStorageService with temporary storage."""
        return FileStorageService(storage_path=temp_storage_path)

    def test_generate_unique_filename(self, storage_service):
        """Test generating unique filename preserves extension."""
        result = storage_service._generate_unique_filename("test.txt")

        assert result.endswith(".txt")
        assert result != "test.txt"
        assert len(result) > 10  # UUID should make it longer

    def test_generate_unique_filename_no_extension(self, storage_service):
        """Test generating unique filename without extension."""
        result = storage_service._generate_unique_filename("test")

        assert result != "test"
        assert "." not in result or result.count(".") == 0

    def test_validate_file_size_success(self, storage_service):
        """Test file size validation passes for valid size."""
        # Should not raise exception
        storage_service.validate_file_size(1024)  # 1KB

    def test_validate_file_size_exceeds_limit(self, storage_service):
        """Test file size validation fails for oversized file."""
        with pytest.raises(ValueError, match="File size.*exceeds maximum"):
            storage_service.validate_file_size(100 * 1024 * 1024)  # 100MB

    def test_validate_mime_type_success(self, storage_service):
        """Test MIME type validation passes for allowed type."""
        # Should not raise exception
        storage_service.validate_mime_type("image/jpeg")

    def test_validate_mime_type_not_allowed(self, storage_service):
        """Test MIME type validation fails for disallowed type."""
        with pytest.raises(ValueError, match="File type.*is not allowed"):
            storage_service.validate_mime_type("application/x-executable")

    @pytest.mark.asyncio
    async def test_save_file_creates_directory(self, storage_service, temp_storage_path):
        """Test that save_file creates account directory if it doesn't exist."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test content")

        await storage_service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename="test.txt",
            mime_type="text/plain",
            size=12,
        )

        # Check directory was created
        account_dir = Path(temp_storage_path) / account_id
        assert account_dir.exists()
        assert account_dir.is_dir()

    @pytest.mark.asyncio
    async def test_save_file_returns_metadata(self, storage_service):
        """Test that save_file returns correct metadata."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test content")

        metadata = await storage_service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename="test.txt",
            mime_type="text/plain",
            size=12,
        )

        assert metadata.filename == "test.txt"
        assert metadata.size == 12
        assert metadata.mime_type == "text/plain"
        assert metadata.path.startswith(f"{account_id}/")
        assert metadata.path.endswith(".txt")

    @pytest.mark.asyncio
    async def test_save_file_stores_content(self, storage_service, temp_storage_path):
        """Test that save_file actually stores the file content."""
        account_id = "test-account-123"
        content = b"test content"
        file_content = BytesIO(content)

        metadata = await storage_service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename="test.txt",
            mime_type="text/plain",
            size=len(content),
        )

        # Read the saved file
        file_path = Path(temp_storage_path) / metadata.path
        assert file_path.exists()

        with open(file_path, "rb") as f:
            saved_content = f.read()

        assert saved_content == content

    @pytest.mark.asyncio
    async def test_save_file_validates_size(self, storage_service):
        """Test that save_file validates file size."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test")

        with pytest.raises(ValueError, match="File size.*exceeds maximum"):
            await storage_service.save_file(
                account_id=account_id,
                file_content=file_content,
                filename="test.txt",
                mime_type="text/plain",
                size=100 * 1024 * 1024,  # 100MB
            )

    @pytest.mark.asyncio
    async def test_save_file_validates_mime_type(self, storage_service):
        """Test that save_file validates MIME type."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test")

        with pytest.raises(ValueError, match="File type.*is not allowed"):
            await storage_service.save_file(
                account_id=account_id,
                file_content=file_content,
                filename="test.exe",
                mime_type="application/x-executable",
                size=4,
            )

    @pytest.mark.asyncio
    async def test_get_file_path_success(self, storage_service, temp_storage_path):
        """Test getting file path for existing file."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test content")

        # Save a file first
        metadata = await storage_service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename="test.txt",
            mime_type="text/plain",
            size=12,
        )

        # Get the file path
        file_path = storage_service.get_file_path(account_id, metadata.path)

        assert file_path.exists()
        assert file_path.is_file()

    def test_get_file_path_wrong_account(self, storage_service):
        """Test that get_file_path rejects files from different account."""
        with pytest.raises(ValueError, match="does not belong to this account"):
            storage_service.get_file_path("account1", "account2/file.txt")

    def test_get_file_path_not_found(self, storage_service):
        """Test that get_file_path raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_file_path("test-account", "test-account/nonexistent.txt")

    def test_get_file_path_traversal_attack(self, storage_service):
        """Test that get_file_path prevents path traversal attacks."""
        with pytest.raises(ValueError, match="Invalid file path"):
            storage_service.get_file_path("test-account", "test-account/../../../etc/passwd")

    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage_service, temp_storage_path):
        """Test deleting a file."""
        account_id = "test-account-123"
        file_content = BytesIO(b"test content")

        # Save a file first
        metadata = await storage_service.save_file(
            account_id=account_id,
            file_content=file_content,
            filename="test.txt",
            mime_type="text/plain",
            size=12,
        )

        # Verify file exists
        file_path = Path(temp_storage_path) / metadata.path
        assert file_path.exists()

        # Delete the file
        storage_service.delete_file(account_id, metadata.path)

        # Verify file is deleted
        assert not file_path.exists()

    def test_delete_file_not_found(self, storage_service):
        """Test that delete_file raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            storage_service.delete_file("test-account", "test-account/nonexistent.txt")

    def test_delete_file_wrong_account(self, storage_service):
        """Test that delete_file rejects files from different account."""
        with pytest.raises(ValueError, match="does not belong to this account"):
            storage_service.delete_file("account1", "account2/file.txt")
