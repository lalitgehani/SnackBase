"""Pydantic schemas for file storage endpoints."""

from pydantic import BaseModel, Field


class FileMetadataResponse(BaseModel):
    """Response schema for file metadata."""

    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    path: str = Field(..., description="Relative path to the file (account_id/uuid_filename)")


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""

    success: bool = Field(default=True, description="Upload success status")
    file: FileMetadataResponse = Field(..., description="Uploaded file metadata")
    message: str = Field(default="File uploaded successfully", description="Success message")
