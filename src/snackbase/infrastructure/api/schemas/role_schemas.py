"""Role API schemas for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class CreateRoleRequest(BaseModel):
    """Request schema for creating a role.

    Attributes:
        name: Role name (e.g., 'editor', 'viewer').
        description: Optional description of the role's purpose.
    """

    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()


class UpdateRoleRequest(BaseModel):
    """Request schema for updating a role.

    Attributes:
        name: Role name.
        description: Optional description of the role's purpose.
    """

    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()


class RoleResponse(BaseModel):
    """Response schema for a role.

    Attributes:
        id: Role ID.
        name: Role name.
        description: Role description.
    """

    id: int
    name: str
    description: str | None = None


class RoleListItem(BaseModel):
    """List item schema for a role.

    Attributes:
        id: Role ID.
        name: Role name.
        description: Role description.
        collections_count: Number of collections this role has permissions for.
    """

    id: int
    name: str
    description: str | None = None
    collections_count: int


class RoleListResponse(BaseModel):
    """Response schema for listing roles.

    Attributes:
        items: List of roles.
        total: Total number of roles.
    """

    items: list[RoleListItem]
    total: int


class CollectionPermission(BaseModel):
    """Permission for a single collection.

    Attributes:
        collection: Collection name.
        permission_id: Permission ID (if exists).
        create: Create operation rule.
        read: Read operation rule.
        update: Update operation rule.
        delete: Delete operation rule.
    """

    collection: str
    permission_id: int | None = None
    create: dict[str, Any] | None = None
    read: dict[str, Any] | None = None
    update: dict[str, Any] | None = None
    delete: dict[str, Any] | None = None


class RolePermissionsResponse(BaseModel):
    """Response schema for role permissions.

    Attributes:
        role_id: Role ID.
        role_name: Role name.
        permissions: List of permissions organized by collection.
    """

    role_id: int
    role_name: str
    permissions: list[CollectionPermission]


class UpdateRolePermissionsRequest(BaseModel):
    """Request schema for updating role permissions.

    Attributes:
        permissions: List of permissions to update.
    """

    permissions: list[dict[str, Any]]


class ValidateRuleRequest(BaseModel):
    """Request schema for validating a permission rule.

    Attributes:
        rule: Rule expression to validate.
    """

    rule: str

    @field_validator("rule")
    @classmethod
    def rule_not_empty(cls, v: str) -> str:
        """Validate that rule is not empty."""
        if not v or not v.strip():
            raise ValueError("Rule expression cannot be empty")
        return v


class ValidateRuleResponse(BaseModel):
    """Response schema for rule validation.

    Attributes:
        valid: Whether the rule is valid.
        error: Error message if invalid.
        position: Error position (line and column) if invalid.
    """

    valid: bool
    error: str | None = None
    position: dict[str, int] | None = None  # {"line": 1, "column": 5}


class TestRuleRequest(BaseModel):
    """Request schema for testing a permission rule.

    Attributes:
        rule: Rule expression to test.
        context: Sample context data for testing.
    """

    rule: str
    context: dict[str, Any]

    @field_validator("rule")
    @classmethod
    def rule_not_empty(cls, v: str) -> str:
        """Validate that rule is not empty."""
        if not v or not v.strip():
            raise ValueError("Rule expression cannot be empty")
        return v


class TestRuleResponse(BaseModel):
    """Response schema for rule testing.

    Attributes:
        allowed: Whether access would be granted.
        error: Error message if evaluation failed.
        evaluation_details: Details about the evaluation.
    """

    allowed: bool
    error: str | None = None
    evaluation_details: str | None = None
