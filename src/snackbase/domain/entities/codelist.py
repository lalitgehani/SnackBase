"""Domain entities and DTOs for codelists."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Codelist:
    """Codelist master entity (system or account scope)."""

    id: str
    code: str
    name: str
    account_id: str
    scope: str  # system | account
    description: str | None = None
    definition: str | None = None
    is_system: bool = False
    is_extensible: bool = False
    is_active: bool = True
    is_builtin: bool = False
    external_code: str | None = None
    version: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Codelist ID is required")
        if not self.code:
            raise ValueError("Codelist code is required")
        if not self.name:
            raise ValueError("Codelist name is required")
        if self.scope not in ("system", "account"):
            raise ValueError("Codelist scope must be 'system' or 'account'")
        if not self.account_id:
            raise ValueError("Codelist account_id is required")


@dataclass
class CodelistValue:
    """Codelist value with stable submission code."""

    id: str
    codelist_id: str
    code: str
    account_id: str
    scope: str  # system | account
    external_code: str | None = None
    sort_order: int = 0
    is_active: bool = True
    is_system: bool = False
    definition: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Value ID is required")
        if not self.code:
            raise ValueError("Value code is required")
        if not self.codelist_id:
            raise ValueError("codelist_id is required")
        if self.scope not in ("system", "account"):
            raise ValueError("Value scope must be 'system' or 'account'")


@dataclass
class CodelistValueLabel:
    """Language-specific label for a value."""

    id: str
    value_id: str
    language: str
    label: str
    description: str | None = None
    is_preferred: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.language or not self.language.strip():
            raise ValueError("Language is required")
        if not self.label or not self.label.strip():
            raise ValueError("Label is required")


@dataclass
class CodelistAccountOverride:
    """Per-account override delta for a value."""

    id: str
    account_id: str
    codelist_id: str
    value_id: str
    visibility: str = "visible"  # visible | hidden
    is_default: bool = False
    sort_order: int | None = None
    metadata_override: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.visibility not in ("visible", "hidden"):
            raise ValueError("visibility must be 'visible' or 'hidden'")


@dataclass
class EffectiveCodelistValue:
    """Resolved effective value DTO for an account + language."""

    code: str
    label: str
    definition: str | None
    metadata: dict[str, Any] | None
    is_default: bool
    sort_order: int
    scope: str
    is_active: bool
    value_id: str
    codelist_id: str
