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
    """

    id: int
    name: str
    description: str | None = None


class RoleListResponse(BaseModel):
    """Response schema for listing roles.

    Attributes:
        items: List of roles.
        total: Total number of roles.
    """

    items: list[RoleListItem]
    total: int
