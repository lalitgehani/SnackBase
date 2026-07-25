"""Integration: migration seeds builtin regions/eu-01 (applies full Alembic chain)."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from snackbase.domain.services.codelist_service import CodelistService
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.codelist import CodelistModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ACCOUNT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.mark.asyncio
async def test_migration_seeds_regions_eu01(db_session):
    """Full migrate creates system regions + eu-01 with EN label."""
    result = await db_session.execute(
        select(CodelistModel).where(CodelistModel.code == "regions")
    )
    regions = result.scalar_one_or_none()
    assert regions is not None
    assert regions.is_builtin is True
    assert regions.is_system is True
    assert regions.account_id == SYSTEM_ACCOUNT_ID

    svc = CodelistService(db_session)
    # Tenant accounts for effective resolution
    for aid, code, slug, name in [
        (ACCOUNT_A, "AA0099", "acct-a-cl", "Account A"),
        (ACCOUNT_B, "BB0099", "acct-b-cl", "Account B"),
    ]:
        if await db_session.get(AccountModel, aid) is None:
            db_session.add(
                AccountModel(id=aid, account_code=code, slug=slug, name=name)
            )
    await db_session.commit()

    for acct in (ACCOUNT_A, ACCOUNT_B):
        eff = await svc.get_effective_values(acct, "regions", "en")
        assert any(e.code == "eu-01" for e in eff)
        eu = next(e for e in eff if e.code == "eu-01")
        assert eu.label == "EU Central (Germany)"

    # No per-account value rows for eu-01
    rows = await db_session.execute(
        text(
            "SELECT account_id FROM codelist_values WHERE code = 'eu-01'"
        )
    )
    owners = {r[0] for r in rows.fetchall()}
    assert owners == {SYSTEM_ACCOUNT_ID}

    # ensure is idempotent after migration seed
    again = await svc.ensure_builtin_regions()
    await db_session.commit()
    assert again.id == regions.id
