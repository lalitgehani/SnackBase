"""Integration: codelist tables exist after migrate with no platform-default rows."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_migration_creates_empty_codelist_tables(db_session: AsyncSession):
    """Full migrate creates codelist tables but does not seed a default dictionary."""
    tables = await db_session.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name LIKE 'codelist%' ORDER BY name"
        )
    )
    names = {r[0] for r in tables.fetchall()}
    assert "codelists" in names
    assert "codelist_values" in names
    assert "codelist_value_labels" in names
    assert "codelist_account_overrides" in names

    count = await db_session.execute(text("SELECT COUNT(*) FROM codelists"))
    assert count.scalar() == 0
