"""Domain service for codelists: CRUD, overrides, effective resolution."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.domain.entities.codelist import EffectiveCodelistValue
from snackbase.infrastructure.persistence.models.codelist import (
    CodelistAccountOverrideModel,
    CodelistModel,
    CodelistValueLabelModel,
    CodelistValueModel,
)
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
    CodelistRepository,
)

logger = get_logger(__name__)

CODELIST_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
VALUE_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")

# Stable seed IDs (must match migration seed)
REGIONS_CODELIST_ID = "00000000-0000-0000-0000-00000000c001"
EU01_VALUE_ID = "00000000-0000-0000-0000-00000000c0e1"
EU01_LABEL_EN_ID = "00000000-0000-0000-0000-00000000c1e1"


class CodelistError(Exception):
    """Base domain error for codelist operations."""

    def __init__(self, message: str, *, code: str = "codelist_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class CodelistNotFoundError(CodelistError):
    def __init__(self, message: str = "Codelist not found") -> None:
        super().__init__(message, code="codelist_not_found")


class CodelistValueNotFoundError(CodelistError):
    def __init__(self, message: str = "Codelist value not found") -> None:
        super().__init__(message, code="codelist_value_not_found")


class CodelistConflictError(CodelistError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="codelist_conflict")


class CodelistForbiddenError(CodelistError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="codelist_forbidden")


class CodelistValidationError(CodelistError):
    def __init__(self, message: str, *, code: str = "codelist_validation") -> None:
        super().__init__(message, code=code)


class CodelistService:
    """Scope-aware codelist domain service.

    Pure domain resolution (get_effective_values, assert_in_codelist, resolve_label)
    is separate from HTTP for unit testability.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CodelistRepository(session)

    # ------------------------------------------------------------------
    # Codelist CRUD
    # ------------------------------------------------------------------

    async def create_codelist(
        self,
        *,
        code: str,
        name: str,
        account_id: str,
        scope: str = "account",
        description: str | None = None,
        definition: str | None = None,
        is_extensible: bool = False,
        is_active: bool = True,
        is_builtin: bool = False,
        external_code: str | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodelistModel:
        if not CODELIST_CODE_PATTERN.match(code):
            raise CodelistValidationError(
                "Codelist code must match ^[a-z][a-z0-9_]*$",
                code="invalid_code",
            )
        if scope not in ("system", "account"):
            raise CodelistValidationError("scope must be 'system' or 'account'")

        is_system = scope == "system"
        owner_account = SYSTEM_ACCOUNT_ID if is_system else account_id

        # Forbid account list shadowing a system list code
        if not is_system:
            existing_system = await self.repo.get_system_codelist_by_code(code)
            if existing_system is not None:
                raise CodelistConflictError(
                    f"Cannot create account codelist '{code}': a system codelist "
                    "with this code already exists"
                )

        if is_system:
            existing = await self.repo.get_system_codelist_by_code(code)
            if existing is not None:
                raise CodelistConflictError(f"System codelist '{code}' already exists")
        else:
            existing = await self.repo.get_account_codelist_by_code(code, owner_account)
            if existing is not None:
                raise CodelistConflictError(
                    f"Codelist '{code}' already exists for this account"
                )

        model = CodelistModel(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=description,
            definition=definition,
            scope=scope,
            account_id=owner_account,
            is_system=is_system,
            is_extensible=is_extensible,
            is_active=is_active,
            is_builtin=is_builtin,
            external_code=external_code,
            version=version,
            metadata_=metadata,
        )
        try:
            return await self.repo.create_codelist(model)
        except IntegrityError as e:
            raise CodelistConflictError(f"Codelist '{code}' already exists") from e

    async def get_codelist(
        self, code: str, *, account_id: str | None = None
    ) -> CodelistModel:
        model = await self.repo.get_codelist_by_code(code, account_id=account_id)
        if model is None:
            raise CodelistNotFoundError(f"Codelist '{code}' not found")
        return model

    async def get_codelist_by_id(self, codelist_id: str) -> CodelistModel:
        model = await self.repo.get_codelist_by_id(codelist_id)
        if model is None:
            raise CodelistNotFoundError(f"Codelist id '{codelist_id}' not found")
        return model

    async def list_codelists(
        self,
        *,
        account_id: str | None = None,
        scope: str | None = None,
        active_only: bool = False,
    ) -> list[CodelistModel]:
        return list(
            await self.repo.list_codelists(
                account_id=account_id,
                scope=scope,
                active_only=active_only,
            )
        )

    async def update_codelist(
        self,
        code: str,
        *,
        account_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        definition: str | None = None,
        is_extensible: bool | None = None,
        is_active: bool | None = None,
        external_code: str | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodelistModel:
        model = await self.get_codelist(code, account_id=account_id)
        if name is not None:
            model.name = name
        if description is not None:
            model.description = description
        if definition is not None:
            model.definition = definition
        if is_extensible is not None:
            model.is_extensible = is_extensible
        if is_active is not None:
            model.is_active = is_active
        if external_code is not None:
            model.external_code = external_code
        if version is not None:
            model.version = version
        if metadata is not None:
            model.metadata_ = metadata
        return await self.repo.update_codelist(model)

    async def delete_codelist(
        self, code: str, *, account_id: str | None = None, hard: bool = False
    ) -> CodelistModel:
        """Delete or soft-deactivate a codelist.

        Builtin/system lists cannot be hard-deleted via domain service
        (soft-deactivate only unless empty and not builtin).
        """
        model = await self.get_codelist(code, account_id=account_id)
        if model.is_builtin:
            if hard:
                raise CodelistForbiddenError(
                    f"Builtin codelist '{code}' cannot be hard-deleted"
                )
            model.is_active = False
            return await self.repo.update_codelist(model)

        if model.is_system and hard:
            # System non-builtin: soft-deactivate preferred; hard only if empty
            values = await self.repo.list_values(
                model.id, include_inactive=True, include_extensions=False
            )
            if values:
                raise CodelistForbiddenError(
                    f"System codelist '{code}' has values; soft-deactivate instead"
                )

        if hard:
            await self.repo.delete_codelist(model)
            return model

        model.is_active = False
        return await self.repo.update_codelist(model)

    # ------------------------------------------------------------------
    # Values
    # ------------------------------------------------------------------

    async def add_value(
        self,
        codelist_code: str,
        *,
        code: str,
        account_id: str,
        definition: str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
        external_code: str | None = None,
        metadata: dict[str, Any] | None = None,
        as_system: bool = False,
    ) -> CodelistValueModel:
        if not VALUE_CODE_PATTERN.match(code):
            raise CodelistValidationError(
                "Value code must be non-empty alphanumeric (with ._-)",
                code="invalid_value_code",
            )

        codelist = await self.get_codelist(codelist_code, account_id=account_id)

        if as_system:
            if not codelist.is_system:
                raise CodelistForbiddenError(
                    "Cannot add system value to a non-system codelist"
                )
            owner = SYSTEM_ACCOUNT_ID
            scope = "system"
            is_system = True
        else:
            # Account extension or account-owned list value
            if codelist.is_system:
                if not codelist.is_extensible:
                    raise CodelistForbiddenError(
                        f"Codelist '{codelist_code}' is not extensible",
                    )
                owner = account_id
                scope = "account"
                is_system = False
            else:
                if codelist.account_id != account_id:
                    raise CodelistForbiddenError(
                        "Cannot add values to another account's codelist"
                    )
                owner = account_id
                scope = "account"
                is_system = False

        existing = await self.repo.get_value_by_code(
            codelist.id, code, account_id=owner
        )
        # Check exact owner uniqueness
        all_vals = await self.repo.list_values(
            codelist.id,
            account_id=owner,
            include_inactive=True,
            include_system=as_system,
            include_extensions=not as_system,
        )
        for v in all_vals:
            if v.code == code and v.account_id == owner:
                raise CodelistConflictError(
                    f"Value code '{code}' already exists on codelist '{codelist_code}'"
                )

        model = CodelistValueModel(
            id=str(uuid.uuid4()),
            codelist_id=codelist.id,
            code=code,
            external_code=external_code,
            sort_order=sort_order,
            is_active=is_active,
            scope=scope,
            account_id=owner,
            is_system=is_system,
            definition=definition,
            metadata_=metadata,
        )
        try:
            return await self.repo.create_value(model)
        except IntegrityError as e:
            raise CodelistConflictError(
                f"Value code '{code}' already exists on codelist '{codelist_code}'"
            ) from e

    async def update_value(
        self,
        codelist_code: str,
        value_code: str,
        *,
        account_id: str,
        definition: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
        external_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodelistValueModel:
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        value = await self.repo.get_value_by_code(
            codelist.id, value_code, account_id=account_id
        )
        if value is None:
            raise CodelistValueNotFoundError(
                f"Value '{value_code}' not found on codelist '{codelist_code}'"
            )
        # Account may only update own extension / own list values
        if not value.is_system and value.account_id != account_id:
            raise CodelistForbiddenError("Cannot update another account's value")

        if definition is not None:
            value.definition = definition
        if sort_order is not None:
            value.sort_order = sort_order
        if is_active is not None:
            value.is_active = is_active
        if external_code is not None:
            value.external_code = external_code
        if metadata is not None:
            value.metadata_ = metadata
        return await self.repo.update_value(value)

    async def deactivate_value(
        self, codelist_code: str, value_code: str, *, account_id: str
    ) -> CodelistValueModel:
        return await self.update_value(
            codelist_code, value_code, account_id=account_id, is_active=False
        )

    async def list_values(
        self,
        codelist_code: str,
        *,
        account_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[CodelistValueModel]:
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        include_ext = bool(codelist.is_extensible or not codelist.is_system)
        return list(
            await self.repo.list_values(
                codelist.id,
                account_id=account_id,
                include_inactive=include_inactive,
                include_system=True,
                include_extensions=include_ext,
            )
        )

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    async def set_label(
        self,
        value_id: str,
        language: str,
        label: str,
        *,
        description: str | None = None,
        is_preferred: bool = True,
    ) -> CodelistValueLabelModel:
        if not language or not language.strip():
            raise CodelistValidationError("Language is required", code="invalid_language")
        if not label or not label.strip():
            raise CodelistValidationError("Label is required", code="invalid_label")

        value = await self.repo.get_value_by_id(value_id)
        if value is None:
            raise CodelistValueNotFoundError(f"Value id '{value_id}' not found")

        model = CodelistValueLabelModel(
            id=str(uuid.uuid4()),
            value_id=value_id,
            language=language.strip().lower(),
            label=label.strip(),
            description=description,
            is_preferred=is_preferred,
        )
        return await self.repo.upsert_label(model)

    async def bulk_upsert_labels(
        self,
        value_id: str,
        labels: list[dict[str, Any]],
    ) -> list[CodelistValueLabelModel]:
        results: list[CodelistValueLabelModel] = []
        for item in labels:
            results.append(
                await self.set_label(
                    value_id,
                    item["language"],
                    item["label"],
                    description=item.get("description"),
                    is_preferred=item.get("is_preferred", True),
                )
            )
        return results

    async def list_labels(self, value_id: str) -> list[CodelistValueLabelModel]:
        return list(await self.repo.list_labels(value_id))

    @staticmethod
    def resolve_label_from_map(
        labels_by_lang: dict[str, str],
        code: str,
        language: str,
        *,
        fallback: str = "en",
    ) -> str:
        """Resolve label: requested → fallback (en) → raw code."""
        lang = (language or fallback).lower()
        if lang in labels_by_lang and labels_by_lang[lang]:
            return labels_by_lang[lang]
        # Primary language without region (e.g. ja-JP → ja)
        primary = lang.split("-")[0]
        if primary in labels_by_lang and labels_by_lang[primary]:
            return labels_by_lang[primary]
        if fallback in labels_by_lang and labels_by_lang[fallback]:
            return labels_by_lang[fallback]
        return code

    async def resolve_label(
        self,
        codelist_code: str,
        value_code: str,
        language: str = "en",
        *,
        account_id: str | None = None,
        include_inactive: bool = True,
    ) -> str:
        """Resolve display label for a code, including inactive values."""
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        value = await self.repo.get_value_by_code(
            codelist.id, value_code, account_id=account_id
        )
        if value is None:
            return value_code
        if not value.is_active and not include_inactive:
            return value_code
        labels = await self.repo.list_labels(value.id)
        by_lang = {lb.language: lb.label for lb in labels if lb.is_preferred or True}
        return self.resolve_label_from_map(by_lang, value.code, language)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    async def set_override(
        self,
        codelist_code: str,
        value_code: str,
        *,
        account_id: str,
        visibility: str = "visible",
        is_default: bool = False,
        sort_order: int | None = None,
        metadata_override: dict[str, Any] | None = None,
    ) -> CodelistAccountOverrideModel:
        if visibility not in ("visible", "hidden"):
            raise CodelistValidationError("visibility must be 'visible' or 'hidden'")

        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        value = await self.repo.get_value_by_code(
            codelist.id, value_code, account_id=account_id
        )
        if value is None:
            raise CodelistValueNotFoundError(
                f"Value '{value_code}' not found on codelist '{codelist_code}'"
            )

        if is_default:
            await self.repo.clear_default_flags(
                account_id, codelist.id, except_value_id=value.id
            )

        existing = await self.repo.get_override(account_id, value.id)
        if existing is not None:
            existing.visibility = visibility
            existing.is_default = is_default
            existing.sort_order = sort_order
            existing.metadata_override = metadata_override
            return await self.repo.update_override(existing)

        model = CodelistAccountOverrideModel(
            id=str(uuid.uuid4()),
            account_id=account_id,
            codelist_id=codelist.id,
            value_id=value.id,
            visibility=visibility,
            is_default=is_default,
            sort_order=sort_order,
            metadata_override=metadata_override,
        )
        try:
            return await self.repo.create_override(model)
        except IntegrityError as e:
            raise CodelistConflictError("Override already exists") from e

    async def clear_override(
        self, codelist_code: str, value_code: str, *, account_id: str
    ) -> None:
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        value = await self.repo.get_value_by_code(
            codelist.id, value_code, account_id=account_id
        )
        if value is None:
            raise CodelistValueNotFoundError(
                f"Value '{value_code}' not found on codelist '{codelist_code}'"
            )
        existing = await self.repo.get_override(account_id, value.id)
        if existing is not None:
            await self.repo.delete_override(existing)

    async def list_overrides(
        self, codelist_code: str, *, account_id: str
    ) -> list[CodelistAccountOverrideModel]:
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        return list(await self.repo.list_overrides(account_id, codelist.id))

    # ------------------------------------------------------------------
    # Effective resolution
    # ------------------------------------------------------------------

    async def get_effective_values(
        self,
        account_id: str,
        codelist_code: str,
        language: str = "en",
        *,
        include_inactive: bool = False,
    ) -> list[EffectiveCodelistValue]:
        """Merge system values + account extensions + overrides + labels.

        Algorithm:
        1. Resolve codelist (system first; account private if no system list)
        2. Candidate values: active system + active account extensions if extensible
           (or all values for account-owned lists)
        3. Apply account overrides (drop hidden; sort/default/metadata merge)
        4. Resolve labels via language fallback
        5. Return ordered DTOs
        """
        codelist = await self.get_codelist(codelist_code, account_id=account_id)

        include_ext = bool(codelist.is_extensible and codelist.is_system) or (
            not codelist.is_system
        )
        values = list(
            await self.repo.list_values(
                codelist.id,
                account_id=account_id,
                include_inactive=include_inactive,
                include_system=True,
                include_extensions=include_ext,
            )
        )

        overrides = await self.repo.list_overrides(account_id, codelist.id)
        override_by_value = {o.value_id: o for o in overrides}

        # Batch load labels (no N+1)
        value_ids = [v.id for v in values]
        all_labels = await self.repo.list_labels_for_values(value_ids)
        labels_by_value: dict[str, dict[str, str]] = {}
        for lb in all_labels:
            labels_by_value.setdefault(lb.value_id, {})[lb.language] = lb.label

        effective: list[EffectiveCodelistValue] = []
        for v in values:
            if not include_inactive and not v.is_active:
                continue
            ov = override_by_value.get(v.id)
            if ov is not None and ov.visibility == "hidden":
                continue

            meta = dict(v.metadata_ or {})
            if ov is not None and ov.metadata_override:
                meta.update(ov.metadata_override)

            sort_order = (
                ov.sort_order
                if ov is not None and ov.sort_order is not None
                else v.sort_order
            )
            is_default = bool(ov.is_default) if ov is not None else False
            label = self.resolve_label_from_map(
                labels_by_value.get(v.id, {}), v.code, language
            )

            effective.append(
                EffectiveCodelistValue(
                    code=v.code,
                    label=label,
                    definition=v.definition,
                    metadata=meta or None,
                    is_default=is_default,
                    sort_order=sort_order,
                    scope=v.scope,
                    is_active=v.is_active,
                    value_id=v.id,
                    codelist_id=codelist.id,
                )
            )

        # Defaults first among equal sort, then sort_order, then code
        effective.sort(key=lambda e: (not e.is_default, e.sort_order, e.code))
        return effective

    async def validate_record_codelist_fields(
        self,
        schema: list[dict[str, Any]],
        data: dict[str, Any],
        account_id: str,
        *,
        allow_inactive_existing: bool = False,
    ) -> list[dict[str, str]]:
        """Validate fields that declare a ``codelist`` option against effective membership.

        Field schema shapes supported:
        - ``{"name": "region", "type": "text", "codelist": "regions"}``
        - ``{"name": "region", "type": "text", "options": {"codelist": "regions"}}``

        Returns a list of error dicts ``{field, message, code}`` (empty if valid).
        """
        errors: list[dict[str, str]] = []
        for field in schema:
            field_name = field.get("name")
            if not field_name:
                continue
            options = field.get("options") if isinstance(field.get("options"), dict) else {}
            codelist_code = field.get("codelist") or options.get("codelist")
            if not codelist_code or field_name not in data:
                continue
            value = data[field_name]
            if value is None or value == "":
                continue
            if not isinstance(value, str):
                errors.append(
                    {
                        "field": field_name,
                        "message": f"Field '{field_name}' must be a string codelist code",
                        "code": "not_in_codelist",
                    }
                )
                continue
            try:
                await self.assert_in_codelist(
                    account_id,
                    str(codelist_code),
                    value,
                    allow_inactive_existing=allow_inactive_existing,
                )
            except CodelistValidationError as e:
                errors.append(
                    {
                        "field": field_name,
                        "message": e.message,
                        "code": "not_in_codelist",
                    }
                )
            except CodelistNotFoundError:
                errors.append(
                    {
                        "field": field_name,
                        "message": f"Codelist '{codelist_code}' not found",
                        "code": "codelist_not_found",
                    }
                )
        return errors

    async def assert_in_codelist(
        self,
        account_id: str,
        codelist_code: str,
        value_code: str,
        *,
        allow_inactive_existing: bool = False,
    ) -> EffectiveCodelistValue:
        """Validate that value_code is in the effective set for the account.

        When allow_inactive_existing=True, inactive (soft-retired) codes that
        still exist on the list are accepted for historical record edits, even
        if they are excluded from pickers. Hidden overrides still fail.
        """
        effective = await self.get_effective_values(
            account_id,
            codelist_code,
            language="en",
            include_inactive=allow_inactive_existing,
        )
        for item in effective:
            if item.code == value_code:
                if not item.is_active and not allow_inactive_existing:
                    continue
                return item

        # If allow_inactive and code exists but was filtered (e.g. hidden), fail
        raise CodelistValidationError(
            f"Value '{value_code}' is not a valid member of codelist "
            f"'{codelist_code}' for this account",
            code="not_in_codelist",
        )

    # ------------------------------------------------------------------
    # Bootstrap / seed
    # ------------------------------------------------------------------

    async def ensure_builtin_regions(self) -> CodelistModel:
        """Idempotently ensure system codelist ``regions`` with ``eu-01`` exists."""
        existing = await self.repo.get_system_codelist_by_code("regions")
        if existing is None:
            existing = CodelistModel(
                id=REGIONS_CODELIST_ID,
                code="regions",
                name="Cloud Regions",
                description="SnackBase Cloud deployment regions",
                definition=None,
                scope="system",
                account_id=SYSTEM_ACCOUNT_ID,
                is_system=True,
                is_extensible=False,
                is_active=True,
                is_builtin=True,
                external_code=None,
                version="1.0",
                metadata_=None,
            )
            try:
                existing = await self.repo.create_codelist(existing)
            except IntegrityError:
                existing = await self.repo.get_system_codelist_by_code("regions")
                if existing is None:
                    raise

        value = await self.repo.get_value_by_code(existing.id, "eu-01")
        if value is None:
            value = CodelistValueModel(
                id=EU01_VALUE_ID,
                codelist_id=existing.id,
                code="eu-01",
                external_code=None,
                sort_order=1,
                is_active=True,
                scope="system",
                account_id=SYSTEM_ACCOUNT_ID,
                is_system=True,
                definition=None,
                metadata_={
                    "country": "DE",
                    "status": "available",
                    "sort_order": 1,
                },
            )
            try:
                value = await self.repo.create_value(value)
            except IntegrityError:
                value = await self.repo.get_value_by_code(existing.id, "eu-01")

        if value is not None:
            label = await self.repo.get_label(value.id, "en")
            if label is None:
                try:
                    await self.repo.create_label(
                        CodelistValueLabelModel(
                            id=EU01_LABEL_EN_ID,
                            value_id=value.id,
                            language="en",
                            label="EU Central (Germany)",
                            description=None,
                            is_preferred=True,
                        )
                    )
                except IntegrityError:
                    pass

        await self.session.flush()
        return existing

    # ------------------------------------------------------------------
    # Import / export (Phase 5 also uses these)
    # ------------------------------------------------------------------

    async def export_codelist_package(
        self, codelist_code: str, *, account_id: str | None = None
    ) -> dict[str, Any]:
        """Export codelist + values + labels as a versioned JSON package."""
        codelist = await self.get_codelist(codelist_code, account_id=account_id)
        values = await self.repo.list_values(
            codelist.id,
            account_id=account_id or SYSTEM_ACCOUNT_ID,
            include_inactive=True,
            include_system=True,
            include_extensions=False if codelist.is_system else True,
        )
        value_ids = [v.id for v in values]
        labels = await self.repo.list_labels_for_values(value_ids)
        labels_by_value: dict[str, list[dict[str, Any]]] = {}
        for lb in labels:
            labels_by_value.setdefault(lb.value_id, []).append(
                {
                    "language": lb.language,
                    "label": lb.label,
                    "description": lb.description,
                    "is_preferred": lb.is_preferred,
                }
            )

        return {
            "format": "snackbase.codelist",
            "format_version": "1.0",
            "codelist": {
                "code": codelist.code,
                "name": codelist.name,
                "description": codelist.description,
                "definition": codelist.definition,
                "scope": codelist.scope,
                "is_extensible": codelist.is_extensible,
                "is_active": codelist.is_active,
                "is_builtin": codelist.is_builtin,
                "external_code": codelist.external_code,
                "version": codelist.version,
                "metadata": codelist.metadata_,
            },
            "values": [
                {
                    "code": v.code,
                    "external_code": v.external_code,
                    "sort_order": v.sort_order,
                    "is_active": v.is_active,
                    "definition": v.definition,
                    "metadata": v.metadata_,
                    "labels": labels_by_value.get(v.id, []),
                }
                for v in values
                if v.is_system or not codelist.is_system
            ],
        }

    async def import_codelist_package(
        self,
        package: dict[str, Any],
        *,
        as_system: bool = True,
        account_id: str = SYSTEM_ACCOUNT_ID,
    ) -> CodelistModel:
        """Idempotent upsert of a codelist package by code."""
        if not isinstance(package, dict):
            raise CodelistValidationError("Package must be a JSON object")
        if package.get("format") != "snackbase.codelist":
            raise CodelistValidationError(
                "Invalid package format; expected snackbase.codelist"
            )
        cl = package.get("codelist")
        if not isinstance(cl, dict) or not cl.get("code") or not cl.get("name"):
            raise CodelistValidationError("Package codelist.code and name are required")
        values = package.get("values")
        if values is not None and not isinstance(values, list):
            raise CodelistValidationError("Package values must be a list")

        code = cl["code"]
        scope = "system" if as_system else "account"
        existing = (
            await self.repo.get_system_codelist_by_code(code)
            if as_system
            else await self.repo.get_account_codelist_by_code(code, account_id)
        )
        if existing is None:
            existing = await self.create_codelist(
                code=code,
                name=cl["name"],
                account_id=account_id,
                scope=scope,
                description=cl.get("description"),
                definition=cl.get("definition"),
                is_extensible=bool(cl.get("is_extensible", False)),
                is_active=bool(cl.get("is_active", True)),
                is_builtin=bool(cl.get("is_builtin", False)),
                external_code=cl.get("external_code"),
                version=cl.get("version"),
                metadata=cl.get("metadata"),
            )
        else:
            existing = await self.update_codelist(
                code,
                account_id=account_id,
                name=cl.get("name"),
                description=cl.get("description"),
                definition=cl.get("definition"),
                is_extensible=cl.get("is_extensible"),
                is_active=cl.get("is_active"),
                external_code=cl.get("external_code"),
                version=cl.get("version"),
                metadata=cl.get("metadata"),
            )

        for v in values or []:
            if not isinstance(v, dict) or not v.get("code"):
                raise CodelistValidationError("Each value requires a code")
            value_code = v["code"]
            found = await self.repo.get_value_by_code(
                existing.id, value_code, account_id=account_id
            )
            if found is None:
                found = await self.add_value(
                    code,
                    code=value_code,
                    account_id=account_id,
                    definition=v.get("definition"),
                    sort_order=int(v.get("sort_order") or 0),
                    is_active=bool(v.get("is_active", True)),
                    external_code=v.get("external_code"),
                    metadata=v.get("metadata"),
                    as_system=as_system,
                )
            else:
                await self.update_value(
                    code,
                    value_code,
                    account_id=account_id if not as_system else SYSTEM_ACCOUNT_ID,
                    definition=v.get("definition"),
                    sort_order=v.get("sort_order"),
                    is_active=v.get("is_active"),
                    external_code=v.get("external_code"),
                    metadata=v.get("metadata"),
                )
            for lb in v.get("labels") or []:
                await self.set_label(
                    found.id,
                    lb["language"],
                    lb["label"],
                    description=lb.get("description"),
                    is_preferred=lb.get("is_preferred", True),
                )

        return existing
