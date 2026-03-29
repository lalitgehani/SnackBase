"""Pydantic schemas for record endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class RecordResponse(BaseModel):
    """Response for a created or retrieved record.

    Contains all system fields plus user-defined fields.
    """

    id: str = Field(..., description="Record ID (UUID)")
    account_id: str = Field(..., description="Account ID the record belongs to")
    created_at: str = Field(..., description="ISO 8601 timestamp when record was created")
    created_by: str = Field(..., description="User ID who created the record")
    updated_at: str = Field(..., description="ISO 8601 timestamp when record was last updated")
    updated_by: str = Field(..., description="User ID who last updated the record")
    account_name: str | None = Field(None, description="Display name for the account (optional)")

    # Additional fields are dynamically added based on collection schema
    # We use model_extra to allow arbitrary fields
    model_config = {"extra": "allow"}

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "RecordResponse":
        """Create a RecordResponse from a record dict.

        Args:
            record: The record dictionary with all fields.

        Returns:
            RecordResponse instance.
        """
        return cls(**record)


class RecordValidationErrorDetail(BaseModel):
    """A single record validation error."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")


class RecordValidationErrorResponse(BaseModel):
    """Response for record validation errors."""

    error: str = Field(default="Validation error", description="Error type")
    details: list[RecordValidationErrorDetail] = Field(
        ..., description="List of validation errors"
    )


class RecordListResponse(BaseModel):
    """Response for listing records."""

    items: list[RecordResponse] = Field(..., description="List of records")
    total: int = Field(..., description="Total number of records matching filter")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Number of records returned")


# ── Batch request bodies ──────────────────────────────────────────────────────


class BatchCreateRequest(BaseModel):
    """Request body for POST /{collection}/batch."""

    records: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of record data objects to create.",
    )


class BatchUpdateItem(BaseModel):
    """A single update item within a batch PATCH request."""

    id: str = Field(..., description="ID of the record to update")
    data: dict[str, Any] = Field(..., description="Fields to update (partial)")


class BatchUpdateRequest(BaseModel):
    """Request body for PATCH /{collection}/batch."""

    records: list[BatchUpdateItem] = Field(
        ...,
        min_length=1,
        description="List of {id, data} pairs to patch.",
    )


class BatchDeleteRequest(BaseModel):
    """Request body for DELETE /{collection}/batch."""

    ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of record IDs to delete.",
    )


# ── Batch response bodies ─────────────────────────────────────────────────────


class BatchValidationError(BaseModel):
    """Error for a single record within a batch operation."""

    error: str = Field(default="validation_error")
    index: int = Field(..., description="Zero-based index of the failing record in the request list")
    details: list[RecordValidationErrorDetail] = Field(...)


class BatchCreateResponse(BaseModel):
    """Response for a successful batch create."""

    created: list[RecordResponse] = Field(..., description="All created records")
    count: int = Field(..., description="Number of records created")


class BatchUpdateResponse(BaseModel):
    """Response for a successful batch update."""

    updated: list[RecordResponse] = Field(..., description="All updated records")
    count: int = Field(..., description="Number of records updated")


class BatchDeleteResponse(BaseModel):
    """Response for a successful batch delete."""

    deleted: list[str] = Field(..., description="IDs of deleted records")
    count: int = Field(..., description="Number of records deleted")
