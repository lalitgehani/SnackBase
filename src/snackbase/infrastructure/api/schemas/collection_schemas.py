"""Pydantic schemas for collection endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FieldDefinition(BaseModel):
    """Definition of a single field in a collection schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Field name (alphanumeric + underscores, starts with letter)",
    )
    type: str = Field(
        ...,
        description="Field type: text, number, boolean, datetime, email, url, json, reference, file, date",
    )
    required: bool = Field(
        default=False,
        description="Whether the field is required",
    )
    default: Any = Field(
        default=None,
        description="Default value for the field",
    )
    unique: bool = Field(
        default=False,
        description="Whether the field value must be unique",
    )
    options: dict | None = Field(
        default=None,
        description="Additional field options",
    )
    # Reference type specific fields
    collection: str | None = Field(
        default=None,
        description="Target collection name (required for reference type)",
    )
    on_delete: str | None = Field(
        default=None,
        description="On delete action: cascade, set_null, restrict (required for reference type)",
    )
    # PII (Personally Identifiable Information) fields
    pii: bool = Field(
        default=False,
        description="Whether this field contains PII data",
    )
    mask_type: str | None = Field(
        default=None,
        description="Mask type for PII fields: email, ssn, phone, name, full, custom",
    )

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize field type to lowercase."""
        return v.lower()

    @field_validator("mask_type")
    @classmethod
    def validate_mask_type(cls, v: str | None, info) -> str | None:
        """Validate mask_type is only set when pii=True and has valid value."""
        if v is None:
            return v

        # Normalize to lowercase
        v = v.lower()

        # Check if pii is True
        pii = info.data.get("pii", False)
        if not pii:
            raise ValueError("mask_type can only be set when pii=True")

        # Validate mask_type value
        valid_mask_types = {"email", "ssn", "phone", "name", "full", "custom"}
        if v not in valid_mask_types:
            raise ValueError(
                f"Invalid mask_type '{v}'. Valid types: {', '.join(sorted(valid_mask_types))}"
            )

        return v


class CreateCollectionRequest(BaseModel):
    """Request body for creating a new collection."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Collection name (3-64 chars, alphanumeric + underscores)",
    )
    fields: list[FieldDefinition] = Field(
        ...,
        min_length=1,
        description="List of field definitions (at least one required)",
        alias="schema",
    )

    model_config = {"populate_by_name": True}


class SchemaFieldResponse(BaseModel):
    """Schema field in collection response."""

    name: str
    type: str
    required: bool = False
    default: Any = None
    unique: bool = False
    options: dict | None = None
    collection: str | None = None
    on_delete: str | None = None
    pii: bool = False
    mask_type: str | None = None


class CollectionResponse(BaseModel):
    """Response for a created collection."""

    id: str = Field(..., description="Collection ID (UUID)")
    name: str = Field(..., description="Collection name")
    table_name: str = Field(..., description="Physical table name in database")
    fields: list[SchemaFieldResponse] = Field(
        ...,
        description="Collection schema",
        serialization_alias="schema",
    )
    created_at: datetime = Field(..., description="When the collection was created")
    updated_at: datetime = Field(..., description="When the collection was last updated")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CollectionListItem(BaseModel):
    """Collection item for list view."""

    id: str = Field(..., description="Collection ID (UUID)")
    name: str = Field(..., description="Collection name")
    table_name: str = Field(..., description="Physical table name in database")
    fields_count: int = Field(..., description="Number of fields in the schema")
    records_count: int = Field(default=0, description="Number of records in the collection")
    created_at: datetime = Field(..., description="When the collection was created")

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    """Paginated list of collections."""

    items: list[CollectionListItem] = Field(..., description="List of collections")
    total: int = Field(..., description="Total number of collections")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class UpdateCollectionRequest(BaseModel):
    """Request body for updating a collection schema."""

    fields: list[FieldDefinition] = Field(
        ...,
        min_length=1,
        description="Updated list of field definitions (at least one required)",
        alias="schema",
    )

    model_config = {"populate_by_name": True}


class GetCollectionsParams(BaseModel):
    """Query parameters for listing collections."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")
    search: str | None = Field(default=None, description="Search term for name or ID")

    model_config = {"from_attributes": True}

