"""Pydantic schemas for migration query API responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MigrationRevisionResponse(BaseModel):
    """Response schema for a single migration revision."""

    model_config = ConfigDict(from_attributes=True)

    revision: str = Field(..., description="Unique revision identifier")
    description: str = Field(..., description="Migration description")
    down_revision: str | None = Field(
        None, description="Previous revision in the chain"
    )
    branch_labels: tuple[str, ...] | None = Field(
        None, description="Branch labels for this revision"
    )
    is_applied: bool = Field(..., description="Whether this revision is applied")
    is_head: bool = Field(..., description="Whether this is the head revision")
    is_dynamic: bool = Field(
        ..., description="Whether this is a dynamic (auto-generated) migration"
    )
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")


class MigrationListResponse(BaseModel):
    """Response schema for listing all migrations."""

    model_config = ConfigDict(from_attributes=True)

    revisions: list[MigrationRevisionResponse] = Field(
        ..., description="List of all revisions"
    )
    total: int = Field(..., description="Total number of revisions")
    current_revision: str | None = Field(
        None, description="Current database revision"
    )


class CurrentRevisionResponse(BaseModel):
    """Response schema for current database revision."""

    model_config = ConfigDict(from_attributes=True)

    revision: str = Field(..., description="Current revision identifier")
    description: str = Field(..., description="Migration description")
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")


class MigrationHistoryItemResponse(BaseModel):
    """Response schema for a single item in migration history."""

    model_config = ConfigDict(from_attributes=True)

    revision: str = Field(..., description="Unique revision identifier")
    description: str = Field(..., description="Migration description")
    is_dynamic: bool = Field(
        ..., description="Whether this is a dynamic (auto-generated) migration"
    )
    created_at: str | None = Field(None, description="Creation timestamp (ISO format)")


class MigrationHistoryResponse(BaseModel):
    """Response schema for migration history."""

    model_config = ConfigDict(from_attributes=True)

    history: list[MigrationHistoryItemResponse] = Field(
        ..., description="List of applied migrations in chronological order"
    )
    total: int = Field(..., description="Total number of applied migrations")
