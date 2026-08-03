"""Pydantic schemas for the Functions API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


def validate_function_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug):
        raise ValueError(
            "Slug must match ^[a-z][a-z0-9_-]{1,63}$ "
            "(start with a letter, 2–64 chars, lowercase alphanumeric/_/-)"
        )
    return slug


class FunctionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=64)
    description: str | None = None
    auth_required: bool = True
    entrypoint: str = "handler.py"

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        return validate_function_slug(v)


class FunctionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    auth_required: bool | None = None
    enabled: bool | None = None
    status: Literal["ACTIVE", "REMOVED", "THROTTLED"] | None = None
    entrypoint: str | None = None


class FunctionDeployRequest(BaseModel):
    entrypoint: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)


class FunctionGrantsUpdateRequest(BaseModel):
    grants: list[str] = Field(
        default_factory=list,
        description="Capability grants e.g. records.read:todos, records.write:orders",
    )


class FunctionTestRequest(BaseModel):
    method: str = "POST"
    path: str = "/"
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    query: dict[str, Any] = Field(default_factory=dict)


class FunctionSecretUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    value: str = Field(..., min_length=1, max_length=49_152)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if v.startswith("SNACKBASE_"):
            raise ValueError("Secret names must not start with SNACKBASE_")
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            raise ValueError("Secret name must be a valid environment variable name")
        return v


class FunctionResponse(BaseModel):
    id: str
    account_id: str
    slug: str
    name: str
    description: str | None
    entrypoint: str
    auth_required: bool
    enabled: bool
    status: str
    active_version_id: str | None
    grants: dict[str, Any] | list[Any]
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FunctionListResponse(BaseModel):
    items: list[FunctionResponse]
    total: int


class FunctionVersionResponse(BaseModel):
    id: str
    function_id: str
    version: int
    dependencies: list[str]
    sha256: str
    env_path: str | None
    created_by: str | None
    created_at: datetime
    # source_files omitted from list; available via body endpoint

    model_config = {"from_attributes": True}


class FunctionVersionListResponse(BaseModel):
    items: list[FunctionVersionResponse]
    total: int


class FunctionBodyResponse(BaseModel):
    version_id: str
    version: int
    entrypoint: str
    files: dict[str, str]
    dependencies: list[str]
    sha256: str


class FunctionExecutionResponse(BaseModel):
    id: str
    function_id: str
    version_id: str | None
    status: str
    http_status: int
    duration_ms: int | None
    request_data: dict[str, Any] | None
    response_body: Any | None
    stdout: str | None
    stderr: str | None
    error_message: str | None
    used_admin_client: bool
    executed_at: datetime

    model_config = {"from_attributes": True}


class FunctionExecutionListResponse(BaseModel):
    items: list[FunctionExecutionResponse]
    total: int


class FunctionSecretResponse(BaseModel):
    id: str
    name: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class FunctionSecretListResponse(BaseModel):
    items: list[FunctionSecretResponse]
    total: int


class FunctionStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    p50_ms: int | None
    p95_ms: int | None
    range: str


class FunctionDeployResponse(BaseModel):
    function: FunctionResponse
    version: FunctionVersionResponse
