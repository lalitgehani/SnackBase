"""Tests for record field codelist option validation (Phase 4)."""

from __future__ import annotations

import pytest

from snackbase.domain.services.codelist_service import CodelistService
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.fixture
async def service(db_session) -> CodelistService:
    if await db_session.get(AccountModel, SYSTEM_ACCOUNT_ID) is None:
        db_session.add(
            AccountModel(
                id=SYSTEM_ACCOUNT_ID,
                account_code="SY0000",
                slug="system",
                name="System",
            )
        )
    if await db_session.get(AccountModel, ACCOUNT_A) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_A,
                account_code="AA0001",
                slug="account-a",
                name="Account A",
            )
        )
    await db_session.commit()
    svc = CodelistService(db_session)
    await svc.ensure_builtin_regions()
    await db_session.commit()
    return svc


@pytest.mark.asyncio
async def test_codelist_field_accepts_eu01(service: CodelistService):
    schema = [
        {"name": "region", "type": "text", "required": True, "codelist": "regions"},
    ]
    errs = await service.validate_record_codelist_fields(
        schema, {"region": "eu-01"}, ACCOUNT_A
    )
    assert errs == []


@pytest.mark.asyncio
async def test_codelist_field_rejects_unknown(service: CodelistService):
    schema = [
        {
            "name": "region",
            "type": "text",
            "options": {"codelist": "regions"},
        },
    ]
    errs = await service.validate_record_codelist_fields(
        schema, {"region": "us-hack"}, ACCOUNT_A
    )
    assert len(errs) == 1
    assert errs[0]["code"] == "not_in_codelist"
    assert errs[0]["field"] == "region"


@pytest.mark.asyncio
async def test_codelist_field_rejects_hidden(service: CodelistService, db_session):
    await service.set_override(
        "regions", "eu-01", account_id=ACCOUNT_A, visibility="hidden"
    )
    await db_session.commit()
    schema = [{"name": "region", "type": "text", "codelist": "regions"}]
    errs = await service.validate_record_codelist_fields(
        schema, {"region": "eu-01"}, ACCOUNT_A
    )
    assert len(errs) == 1
    assert errs[0]["code"] == "not_in_codelist"
