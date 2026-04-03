"""Pydantic schemas for the custom endpoints API (F8.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Valid HTTP methods for custom endpoints
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# Built-in route prefixes that custom endpoint paths must not shadow
RESERVED_PATH_PREFIXES = {
    "/auth",
    "/collections",
    "/accounts",
    "/users",
    "/roles",
    "/permissions",
    "/macros",
    "/groups",
    "/invitations",
    "/api-keys",
    "/dashboard",
    "/audit-logs",
    "/migrations",
    "/admin",
    "/oauth",
    "/saml",
    "/collection-rules",
    "/email-templates",
    "/files",
    "/realtime",
    "/webhooks",
    "/jobs",
    "/hooks",
    "/endpoints",
    "/records",
    "/x",
}


def _validate_endpoint_path(path: str) -> str:
    """Validate a custom endpoint path.

    Rules:
    - Must start with /
    - Only alphanumeric, -, _, /, : characters
    - Must not start with a reserved prefix
    """
    import re

    if not path.startswith("/"):
        raise ValueError("Path must start with '/'")

    if not re.match(r"^[a-zA-Z0-9/_:.-]+$", path):
        raise ValueError(
            "Path may only contain alphanumeric characters, -, _, /, : and ."
        )

    # Check reserved prefixes — normalise to lowercase for comparison
    path_lower = path.lower()
    for prefix in RESERVED_PATH_PREFIXES:
        # Path starts with the reserved prefix (exact or followed by / or end)
        if path_lower == prefix or path_lower.startswith(prefix + "/"):
            raise ValueError(
                f"Path '{path}' conflicts with a built-in route prefix '{prefix}'"
            )

    return path


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class EndpointCreateRequest(BaseModel):
    """Request body for creating a custom endpoint."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable name")
    description: str | None = Field(None, description="Optional description")
    path: str = Field(
        ...,
        description=(
            "URL path starting with /. Supports :param segments "
            "(e.g. /users/:user_id/orders). Must not shadow built-in routes."
        ),
    )
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ..., description="HTTP method"
    )
    auth_required: bool = Field(
        True,
        description="Whether a valid auth token is required (default: true)",
    )
    condition: str | None = Field(
        None,
        description="Optional rule expression; request denied (403) if it evaluates False",
    )
    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of action configs to execute sequentially",
    )
    response_template: dict[str, Any] | None = Field(
        None,
        description=(
            "HTTP response template: "
            '{"status": 200, "body": {...}, "headers": {...}}. '
            "Supports {{template}} variables from request context and action results."
        ),
    )
    enabled: bool = Field(True, description="Whether the endpoint is active on creation")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        return _validate_endpoint_path(v)

    @field_validator("method")
    @classmethod
    def normalise_method(cls, v: str) -> str:
        return v.upper()


class EndpointUpdateRequest(BaseModel):
    """Request body for updating a custom endpoint (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    path: str | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    auth_required: bool | None = None
    condition: str | None = Field(
        None, description="Pass '' to clear the condition expression"
    )
    actions: list[dict[str, Any]] | None = None
    response_template: dict[str, Any] | None = None
    enabled: bool | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_endpoint_path(v)
        return v

    @field_validator("method")
    @classmethod
    def normalise_method(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EndpointResponse(BaseModel):
    """Response schema for a single custom endpoint."""

    id: str
    account_id: str
    name: str
    description: str | None
    path: str
    method: str
    auth_required: bool
    condition: str | None
    actions: list[dict[str, Any]]
    response_template: dict[str, Any] | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = {"from_attributes": True}


class EndpointListResponse(BaseModel):
    """Paginated list of custom endpoints."""

    items: list[EndpointResponse]
    total: int


# ---------------------------------------------------------------------------
# Execution history schemas
# ---------------------------------------------------------------------------


class EndpointExecutionResponse(BaseModel):
    """Response schema for a single endpoint execution record."""

    id: str
    endpoint_id: str
    status: str
    http_status: int
    duration_ms: int | None
    request_data: dict[str, Any] | None
    response_body: dict[str, Any] | None
    error_message: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}


class EndpointExecutionListResponse(BaseModel):
    """Paginated list of endpoint executions."""

    items: list[EndpointExecutionResponse]
    total: int
