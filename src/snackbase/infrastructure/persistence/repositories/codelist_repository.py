"""Repository for codelist, value, label, and override persistence."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snackbase.infrastructure.persistence.models.codelist import (
    CodelistAccountOverrideModel,
    CodelistModel,
    CodelistValueLabelModel,
    CodelistValueModel,
)

SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


class CodelistRepository:
    """Data access for codelists and related tables."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Codelists
    # ------------------------------------------------------------------

    async def create_codelist(self, model: CodelistModel) -> CodelistModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_codelist_by_id(self, codelist_id: str) -> CodelistModel | None:
        result = await self.session.execute(
            select(CodelistModel).where(CodelistModel.id == codelist_id)
        )
        return result.scalar_one_or_none()

    async def get_codelist_by_code(
        self,
        code: str,
        *,
        account_id: str | None = None,
        prefer_account: bool = True,
    ) -> CodelistModel | None:
        """Resolve a codelist by code.

        When prefer_account is True and account_id is set, returns the
        account-owned list if present; otherwise falls back to system list.
        Account shadow of system list codes is forbidden by product rule —
        account lists with the same code as a system list are still resolvable
        only when explicitly preferred; default resolution prefers account-owned
        only when no system list exists, OR account-owned when product allows.
        Plan: forbid same-code account shadow of system lists — resolve system
        first if a system list exists with that code; account list only if no
        system list.
        """
        # Prefer system list if it exists (forbid account shadow of system codes)
        system_result = await self.session.execute(
            select(CodelistModel).where(
                and_(
                    CodelistModel.code == code,
                    CodelistModel.is_system == True,  # noqa: E712
                    CodelistModel.account_id == SYSTEM_ACCOUNT_ID,
                )
            )
        )
        system_list = system_result.scalar_one_or_none()
        if system_list is not None:
            return system_list

        if account_id is not None:
            acct_result = await self.session.execute(
                select(CodelistModel).where(
                    and_(
                        CodelistModel.code == code,
                        CodelistModel.account_id == account_id,
                        CodelistModel.is_system == False,  # noqa: E712
                    )
                )
            )
            return acct_result.scalar_one_or_none()

        return None

    async def get_account_codelist_by_code(
        self, code: str, account_id: str
    ) -> CodelistModel | None:
        result = await self.session.execute(
            select(CodelistModel).where(
                and_(
                    CodelistModel.code == code,
                    CodelistModel.account_id == account_id,
                    CodelistModel.is_system == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_system_codelist_by_code(self, code: str) -> CodelistModel | None:
        result = await self.session.execute(
            select(CodelistModel).where(
                and_(
                    CodelistModel.code == code,
                    CodelistModel.is_system == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_codelists(
        self,
        *,
        account_id: str | None = None,
        scope: str | None = None,
        include_system: bool = True,
        active_only: bool = False,
    ) -> Sequence[CodelistModel]:
        filters = []
        if active_only:
            filters.append(CodelistModel.is_active == True)  # noqa: E712
        if scope == "system":
            filters.append(CodelistModel.is_system == True)  # noqa: E712
        elif scope == "account":
            filters.append(CodelistModel.is_system == False)  # noqa: E712
            if account_id:
                filters.append(CodelistModel.account_id == account_id)
        else:
            # Visible: system lists + own account lists
            if account_id is not None:
                visibility = or_(
                    CodelistModel.is_system == True,  # noqa: E712
                    CodelistModel.account_id == account_id,
                )
                filters.append(visibility)
            elif not include_system:
                filters.append(CodelistModel.is_system == False)  # noqa: E712

        query = select(CodelistModel)
        if filters:
            query = query.where(and_(*filters))
        query = query.order_by(CodelistModel.is_system.desc(), CodelistModel.code.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_codelist(self, model: CodelistModel) -> CodelistModel:
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_codelist(self, model: CodelistModel) -> None:
        await self.session.delete(model)
        await self.session.flush()

    # ------------------------------------------------------------------
    # Values
    # ------------------------------------------------------------------

    async def create_value(self, model: CodelistValueModel) -> CodelistValueModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_value_by_id(self, value_id: str) -> CodelistValueModel | None:
        result = await self.session.execute(
            select(CodelistValueModel)
            .options(selectinload(CodelistValueModel.labels))
            .where(CodelistValueModel.id == value_id)
        )
        return result.scalar_one_or_none()

    async def get_value_by_code(
        self,
        codelist_id: str,
        code: str,
        *,
        account_id: str | None = None,
    ) -> CodelistValueModel | None:
        """Get value by code; prefer system value, then account extension."""
        filters = [
            CodelistValueModel.codelist_id == codelist_id,
            CodelistValueModel.code == code,
        ]
        if account_id is not None:
            filters.append(
                or_(
                    CodelistValueModel.account_id == SYSTEM_ACCOUNT_ID,
                    CodelistValueModel.account_id == account_id,
                )
            )
        result = await self.session.execute(
            select(CodelistValueModel)
            .options(selectinload(CodelistValueModel.labels))
            .where(and_(*filters))
            .order_by(CodelistValueModel.is_system.desc())
        )
        return result.scalars().first()

    async def list_values(
        self,
        codelist_id: str,
        *,
        account_id: str | None = None,
        include_inactive: bool = False,
        include_system: bool = True,
        include_extensions: bool = True,
    ) -> Sequence[CodelistValueModel]:
        filters = [CodelistValueModel.codelist_id == codelist_id]
        if not include_inactive:
            filters.append(CodelistValueModel.is_active == True)  # noqa: E712

        owner_filters = []
        if include_system:
            owner_filters.append(CodelistValueModel.is_system == True)  # noqa: E712
        if include_extensions and account_id is not None:
            owner_filters.append(
                and_(
                    CodelistValueModel.is_system == False,  # noqa: E712
                    CodelistValueModel.account_id == account_id,
                )
            )
        elif include_extensions and account_id is None:
            owner_filters.append(CodelistValueModel.is_system == False)  # noqa: E712

        if owner_filters:
            filters.append(or_(*owner_filters))

        result = await self.session.execute(
            select(CodelistValueModel)
            .options(selectinload(CodelistValueModel.labels))
            .where(and_(*filters))
            .order_by(CodelistValueModel.sort_order.asc(), CodelistValueModel.code.asc())
        )
        return result.scalars().all()

    async def update_value(self, model: CodelistValueModel) -> CodelistValueModel:
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_value(self, model: CodelistValueModel) -> None:
        await self.session.delete(model)
        await self.session.flush()

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    async def create_label(self, model: CodelistValueLabelModel) -> CodelistValueLabelModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_label(
        self, value_id: str, language: str
    ) -> CodelistValueLabelModel | None:
        result = await self.session.execute(
            select(CodelistValueLabelModel).where(
                and_(
                    CodelistValueLabelModel.value_id == value_id,
                    CodelistValueLabelModel.language == language,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_labels(self, value_id: str) -> Sequence[CodelistValueLabelModel]:
        result = await self.session.execute(
            select(CodelistValueLabelModel)
            .where(CodelistValueLabelModel.value_id == value_id)
            .order_by(CodelistValueLabelModel.language.asc())
        )
        return result.scalars().all()

    async def list_labels_for_values(
        self, value_ids: list[str]
    ) -> Sequence[CodelistValueLabelModel]:
        if not value_ids:
            return []
        result = await self.session.execute(
            select(CodelistValueLabelModel).where(
                CodelistValueLabelModel.value_id.in_(value_ids)
            )
        )
        return result.scalars().all()

    async def upsert_label(
        self, model: CodelistValueLabelModel
    ) -> CodelistValueLabelModel:
        existing = await self.get_label(model.value_id, model.language)
        if existing is not None:
            existing.label = model.label
            existing.description = model.description
            existing.is_preferred = model.is_preferred
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        return await self.create_label(model)

    async def delete_label(self, model: CodelistValueLabelModel) -> None:
        await self.session.delete(model)
        await self.session.flush()

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    async def create_override(
        self, model: CodelistAccountOverrideModel
    ) -> CodelistAccountOverrideModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_override(
        self, account_id: str, value_id: str
    ) -> CodelistAccountOverrideModel | None:
        result = await self.session.execute(
            select(CodelistAccountOverrideModel).where(
                and_(
                    CodelistAccountOverrideModel.account_id == account_id,
                    CodelistAccountOverrideModel.value_id == value_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_overrides(
        self, account_id: str, codelist_id: str
    ) -> Sequence[CodelistAccountOverrideModel]:
        result = await self.session.execute(
            select(CodelistAccountOverrideModel).where(
                and_(
                    CodelistAccountOverrideModel.account_id == account_id,
                    CodelistAccountOverrideModel.codelist_id == codelist_id,
                )
            )
        )
        return result.scalars().all()

    async def update_override(
        self, model: CodelistAccountOverrideModel
    ) -> CodelistAccountOverrideModel:
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_override(self, model: CodelistAccountOverrideModel) -> None:
        await self.session.delete(model)
        await self.session.flush()

    async def clear_default_flags(
        self, account_id: str, codelist_id: str, *, except_value_id: str | None = None
    ) -> None:
        """Clear is_default on all overrides for account+codelist except one value."""
        overrides = await self.list_overrides(account_id, codelist_id)
        for ov in overrides:
            if except_value_id is not None and ov.value_id == except_value_id:
                continue
            if ov.is_default:
                ov.is_default = False
        await self.session.flush()

    async def delete_overrides_for_account_value(
        self, account_id: str, value_id: str
    ) -> None:
        await self.session.execute(
            delete(CodelistAccountOverrideModel).where(
                and_(
                    CodelistAccountOverrideModel.account_id == account_id,
                    CodelistAccountOverrideModel.value_id == value_id,
                )
            )
        )
        await self.session.flush()
