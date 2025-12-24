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
        description="Field type: text, number, boolean, datetime, email, url, json, reference",
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

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize field type to lowercase."""
        return v.lower()


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
