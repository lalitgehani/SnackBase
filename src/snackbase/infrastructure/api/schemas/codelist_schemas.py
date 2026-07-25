"""Pydantic schemas for Codelist API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodelistCreateRequest(BaseModel):
    """Create a codelist (system or account scope)."""

    code: str = Field(..., min_length=1, max_length=100, description="Stable identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    definition: str | None = None
    scope: Literal["system", "account"] = "account"
    is_extensible: bool = False
    is_active: bool = True
    external_code: str | None = None
    version: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("code must match ^[a-z][a-z0-9_]*$")
        return v


class CodelistUpdateRequest(BaseModel):
    """Update mutable codelist fields (code is immutable)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    definition: str | None = None
    is_extensible: bool | None = None
    is_active: bool | None = None
    external_code: str | None = None
    version: str | None = None
    metadata: dict[str, Any] | None = None


class CodelistResponse(BaseModel):
    """Codelist metadata response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str | None = None
    definition: str | None = None
    scope: str
    account_id: str
    is_system: bool
    is_extensible: bool
    is_active: bool
    is_builtin: bool
    external_code: str | None = None
    version: str | None = None
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LabelUpsertRequest(BaseModel):
    """Upsert a language label for a value."""

    language: str = Field(..., min_length=1, max_length=20)
    label: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    is_preferred: bool = True


class CodelistValueCreateRequest(BaseModel):
    """Create a codelist value (system or account extension)."""

    code: str = Field(..., min_length=1, max_length=100)
    definition: str | None = None
    sort_order: int = 0
    is_active: bool = True
    external_code: str | None = None
    metadata: dict[str, Any] | None = None
    labels: list[LabelUpsertRequest] | None = None


class CodelistValueUpdateRequest(BaseModel):
    """Update a codelist value (code immutable)."""

    definition: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    external_code: str | None = None
    metadata: dict[str, Any] | None = None


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    value_id: str
    language: str
    label: str
    description: str | None = None
    is_preferred: bool = True


class CodelistValueResponse(BaseModel):
    """Raw value row (admin management)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    codelist_id: str
    code: str
    external_code: str | None = None
    sort_order: int = 0
    is_active: bool = True
    scope: str
    account_id: str
    is_system: bool
    definition: str | None = None
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    labels: list[LabelResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EffectiveValueResponse(BaseModel):
    """Effective value DTO for pickers."""

    code: str
    label: str
    definition: str | None = None
    metadata: dict[str, Any] | None = None
    is_default: bool = False
    sort_order: int = 0
    scope: str
    is_active: bool = True
    value_id: str | None = None


class OverrideRequest(BaseModel):
    """Set account override for a value."""

    visibility: Literal["visible", "hidden"] = "visible"
    is_default: bool = False
    sort_order: int | None = None
    metadata_override: dict[str, Any] | None = None


class OverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    codelist_id: str
    value_id: str
    visibility: str
    is_default: bool
    sort_order: int | None = None
    metadata_override: dict[str, Any] | None = None


class CodelistPackageImportRequest(BaseModel):
    """Import a versioned codelist package."""

    package: dict[str, Any]


class MessageResponse(BaseModel):
    message: str
