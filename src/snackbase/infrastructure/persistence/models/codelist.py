"""SQLAlchemy models for first-class codelists (shared reference dictionaries).

Codelists mirror the configurations multi-tenancy pattern:
- account_id is always populated (system account UUID for system lists)
- is_system / is_builtin flags control scope and mutability
- Values store stable submission codes; labels resolve at read time
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from snackbase.infrastructure.persistence.database import Base


class CodelistModel(Base):
    """Master codelist entity (system-shared or account-private dictionary)."""

    __tablename__ = "codelists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="Codelist ID (UUID)")
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Stable codelist identifier (e.g. regions)",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Display name")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Formal definition / notes"
    )
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="system | account",
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Always populated; system account UUID for system lists",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="True for system-scope lists"
    )
    is_extensible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="Account may add extension values when true",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="Builtin lists cannot be hard-deleted"
    )
    external_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="External terminology code (e.g. CDISC)"
    )
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    values: Mapped[list[CodelistValueModel]] = relationship(
        "CodelistValueModel",
        back_populates="codelist",
        cascade="all, delete-orphan",
    )
    overrides: Mapped[list[CodelistAccountOverrideModel]] = relationship(
        "CodelistAccountOverrideModel",
        back_populates="codelist",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # System lists share system account_id; account lists unique per tenant
        UniqueConstraint("account_id", "code", name="uq_codelists_account_code"),
        Index("ix_codelists_code", "code"),
        Index("ix_codelists_account_id", "account_id"),
        Index("ix_codelists_is_system", "is_system"),
        Index("ix_codelists_scope", "scope"),
    )

    def __repr__(self) -> str:
        return f"<Codelist(id={self.id}, code={self.code}, scope={self.scope})>"


class CodelistValueModel(Base):
    """Codelist value (decode / term) with stable submission code."""

    __tablename__ = "codelist_values"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    codelist_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("codelists.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Stable submission value"
    )
    external_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="system | account (extension)"
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        comment="System account for system values; tenant for extensions",
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    codelist: Mapped[CodelistModel] = relationship("CodelistModel", back_populates="values")
    labels: Mapped[list[CodelistValueLabelModel]] = relationship(
        "CodelistValueLabelModel",
        back_populates="value",
        cascade="all, delete-orphan",
    )
    overrides: Mapped[list[CodelistAccountOverrideModel]] = relationship(
        "CodelistAccountOverrideModel",
        back_populates="value",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "codelist_id",
            "code",
            "account_id",
            name="uq_codelist_values_list_code_account",
        ),
        Index("ix_codelist_values_codelist_id", "codelist_id"),
        Index("ix_codelist_values_account_id", "account_id"),
        Index("ix_codelist_values_code", "code"),
        Index("ix_codelist_values_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CodelistValue(id={self.id}, code={self.code})>"


class CodelistValueLabelModel(Base):
    """Language-specific label for a codelist value."""

    __tablename__ = "codelist_value_labels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    value_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("codelist_values.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="BCP-47 language tag (en, ja)"
    )
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    value: Mapped[CodelistValueModel] = relationship(
        "CodelistValueModel", back_populates="labels"
    )

    __table_args__ = (
        # One preferred label row per (value, language) in v1
        UniqueConstraint(
            "value_id",
            "language",
            name="uq_codelist_value_labels_value_language",
        ),
        Index("ix_codelist_value_labels_value_id", "value_id"),
        Index("ix_codelist_value_labels_language", "language"),
    )

    def __repr__(self) -> str:
        return f"<CodelistValueLabel(value_id={self.value_id}, lang={self.language})>"


class CodelistAccountOverrideModel(Base):
    """Per-account delta for a shared codelist value (hide/default/sort/metadata)."""

    __tablename__ = "codelist_account_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    codelist_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("codelists.id", ondelete="CASCADE"),
        nullable=False,
    )
    value_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("codelist_values.id", ondelete="CASCADE"),
        nullable=False,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="visible",
        comment="visible | hidden",
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_override: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    codelist: Mapped[CodelistModel] = relationship(
        "CodelistModel", back_populates="overrides"
    )
    value: Mapped[CodelistValueModel] = relationship(
        "CodelistValueModel", back_populates="overrides"
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "value_id",
            name="uq_codelist_overrides_account_value",
        ),
        Index("ix_codelist_overrides_account_id", "account_id"),
        Index("ix_codelist_overrides_codelist_id", "codelist_id"),
        Index("ix_codelist_overrides_value_id", "value_id"),
        Index("ix_codelist_overrides_account_value", "account_id", "value_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CodelistAccountOverride(account={self.account_id}, "
            f"value={self.value_id}, visibility={self.visibility})>"
        )
