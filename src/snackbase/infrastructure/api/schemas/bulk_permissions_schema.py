"""Bulk permissions API schemas for request/response validation."""

from pydantic import BaseModel, field_validator


class BulkPermissionUpdate(BaseModel):
    """Schema for a single permission update in bulk operation.

    Attributes:
        collection: Collection name.
        operation: Operation type (create, read, update, delete).
        rule: Rule expression.
        fields: Fields allowed (list of field names or '*' for all).
    """

    collection: str
    operation: str
    rule: str
    fields: list[str] | str

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate that operation is one of the allowed values."""
        allowed = {"create", "read", "update", "delete"}
        if v not in allowed:
            raise ValueError(f"Operation must be one of {allowed}")
        return v

    @field_validator("collection")
    @classmethod
    def collection_not_empty(cls, v: str) -> str:
        """Validate that collection is not empty."""
        if not v or not v.strip():
            raise ValueError("Collection name cannot be empty")
        return v.strip()

    @field_validator("rule")
    @classmethod
    def rule_not_empty(cls, v: str) -> str:
        """Validate that rule is not empty."""
        if not v or not v.strip():
            raise ValueError("Rule expression cannot be empty")
        return v


class BulkPermissionUpdateRequest(BaseModel):
    """Request schema for bulk permission updates.

    Attributes:
        updates: List of permission updates to apply.
    """

    updates: list[BulkPermissionUpdate]

    @field_validator("updates")
    @classmethod
    def updates_not_empty(cls, v: list[BulkPermissionUpdate]) -> list[BulkPermissionUpdate]:
        """Validate that updates list is not empty."""
        if not v:
            raise ValueError("Updates list cannot be empty")
        return v


class BulkPermissionUpdateResponse(BaseModel):
    """Response schema for bulk permission updates.

    Attributes:
        success_count: Number of successful updates.
        failure_count: Number of failed updates.
        errors: List of error messages for failed updates.
    """

    success_count: int
    failure_count: int
    errors: list[str]
