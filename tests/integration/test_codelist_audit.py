"""Audit logging for codelist mutations (Phase 5.6).

Uses enable_audit_hooks so SQLAlchemy listeners capture CREATE on codelist tables.
Hard-fails when expected audit rows are missing (no theater assertions).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.context import clear_current_context, set_current_context
from snackbase.domain.entities.hook_context import HookContext
from snackbase.domain.services.codelist_service import CodelistService
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.audit_log import AuditLogModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

pytestmark = pytest.mark.enable_audit_hooks

ACCOUNT_A = "dddddddd-dddd-dddd-dddd-dddddddddddd"


@dataclass
class MockUser:
    id: str
    email: str


@pytest.mark.asyncio
async def test_codelist_create_produces_audit_entry(db_session: AsyncSession):
    """Mutating a system codelist produces CREATE audit log when audit hooks are on."""
    if await db_session.get(AccountModel, SYSTEM_ACCOUNT_ID) is None:
        db_session.add(
            AccountModel(
                id=SYSTEM_ACCOUNT_ID,
                account_code="SY0000",
                slug="system",
                name="System",
            )
        )
        await db_session.commit()

    set_current_context(
        HookContext(
            app=None,
            user=MockUser(id="superadmin-audit", email="admin@example.com"),
            account_id=SYSTEM_ACCOUNT_ID,
            request_id="req-codelist-audit",
            ip_address="127.0.0.1",
            user_agent="pytest",
            user_name="Superadmin",
        )
    )
    try:
        svc = CodelistService(db_session)
        created = await svc.create_codelist(
            code="audit_list",
            name="Audit List",
            account_id=SYSTEM_ACCOUNT_ID,
            scope="system",
        )
        await db_session.commit()

        result = await db_session.execute(
            select(AuditLogModel).where(
                AuditLogModel.table_name == "codelists",
                AuditLogModel.operation == "CREATE",
            )
        )
        rows = result.scalars().all()
        assert len(rows) >= 1, (
            "Expected CREATE audit log entry for codelists when enable_audit_hooks is set"
        )
        assert any(r.record_id == created.id for r in rows), (
            f"Expected audit record_id={created.id}, got {[r.record_id for r in rows]}"
        )
        assert all(r.operation == "CREATE" for r in rows)
        assert all(r.table_name == "codelists" for r in rows)
    finally:
        clear_current_context()


@pytest.mark.asyncio
async def test_override_hide_produces_audit_entry(db_session: AsyncSession):
    """Override hide must produce CREATE audit on codelist_account_overrides."""
    for aid, code, slug, name in [
        (SYSTEM_ACCOUNT_ID, "SY0000", "system", "System"),
        (ACCOUNT_A, "DD0001", "acct-d", "Account D"),
    ]:
        if await db_session.get(AccountModel, aid) is None:
            db_session.add(
                AccountModel(id=aid, account_code=code, slug=slug, name=name)
            )
    await db_session.commit()

    set_current_context(
        HookContext(
            app=None,
            user=MockUser(id="admin-a", email="a@example.com"),
            account_id=ACCOUNT_A,
            request_id="req-override-audit",
            ip_address="127.0.0.1",
            user_agent="pytest",
            user_name="Admin A",
        )
    )
    try:
        svc = CodelistService(db_session)
        await svc.create_codelist(
            code="audit_ov",
            name="Audit OV",
            account_id=SYSTEM_ACCOUNT_ID,
            scope="system",
        )
        await svc.add_value(
            "audit_ov",
            code="v1",
            account_id=SYSTEM_ACCOUNT_ID,
            as_system=True,
        )
        await db_session.commit()
        ov = await svc.set_override(
            "audit_ov", "v1", account_id=ACCOUNT_A, visibility="hidden"
        )
        await db_session.commit()

        assert ov.visibility == "hidden"

        result = await db_session.execute(
            select(AuditLogModel).where(
                AuditLogModel.table_name == "codelist_account_overrides",
                AuditLogModel.operation == "CREATE",
            )
        )
        rows = result.scalars().all()
        assert len(rows) >= 1, (
            "Expected CREATE audit log for codelist_account_overrides on hide override"
        )
        assert any(r.record_id == ov.id for r in rows), (
            f"Expected audit record_id={ov.id}, got {[r.record_id for r in rows]}"
        )
        assert all(r.table_name == "codelist_account_overrides" for r in rows)
    finally:
        clear_current_context()
