"""Permission API schemas for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class OperationRuleSchema(BaseModel):
    """Schema for a single CRUD operation rule.

    Attributes:
        rule: Expression string (e.g., "true", "user.id == record.owner_id").
        fields: List of allowed fields or "*" for all fields.
    """

    rule: str
    fields: list[str] | str = "*"

    @field_validator("rule")
    @classmethod
    def rule_not_empty(cls, v: str) -> str:
        """Validate that rule is not empty."""
        if not v or not v.strip():
            raise ValueError("Rule expression cannot be empty")
        return v

    @field_validator("fields")
    @classmethod
    def fields_valid(cls, v: list[str] | str) -> list[str] | str:
        """Validate that fields is "*" or a list of strings."""
        if v == "*":
            return v
        if not isinstance(v, list):
            raise ValueError("Fields must be '*' or a list of field names")
        if not all(isinstance(f, str) and f.strip() for f in v):
            raise ValueError("Field names must be non-empty strings")
        return v


class PermissionRulesSchema(BaseModel):
    """Schema for CRUD operation rules.

    Each operation is optional - if None, that operation is not permitted.

    Attributes:
        create: Rule for create operations.
        read: Rule for read operations.
        update: Rule for update operations.
        delete: Rule for delete operations.
    """

    create: OperationRuleSchema | None = None
    read: OperationRuleSchema | None = None
    update: OperationRuleSchema | None = None
    delete: OperationRuleSchema | None = None


class CreatePermissionRequest(BaseModel):
    """Request schema for creating a permission.

    Attributes:
        role_id: ID of the role this permission applies to.
        collection: Collection name (* for all collections).
        rules: CRUD operation rules.
    """

    role_id: int
    collection: str
    rules: PermissionRulesSchema

    @field_validator("collection")
    @classmethod
    def collection_not_empty(cls, v: str) -> str:
        """Validate that collection is not empty."""
        if not v or not v.strip():
            raise ValueError("Collection name cannot be empty")
        return v

    @field_validator("role_id")
    @classmethod
    def role_id_positive(cls, v: int) -> int:
        """Validate that role_id is positive."""
        if v <= 0:
            raise ValueError("Role ID must be a positive integer")
        return v


class PermissionResponse(BaseModel):
    """Response schema for a permission.

    Attributes:
        id: Permission ID.
        role_id: Role ID this permission applies to.
        collection: Collection name.
        rules: CRUD operation rules.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    id: int
    role_id: int
    collection: str
    rules: PermissionRulesSchema
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    """Response schema for listing permissions.

    Attributes:
        items: List of permissions.
        total: Total number of permissions.
    """

    items: list[PermissionResponse]
    total: int
