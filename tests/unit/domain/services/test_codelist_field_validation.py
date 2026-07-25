"""Tests for record field codelist option validation."""

from __future__ import annotations

import pytest

from snackbase.domain.services.codelist_service import CodelistService
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


async def _seed_priority_list(svc: CodelistService, db_session) -> None:
    await svc.create_codelist(
        code="priority",
        name="Priority",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await svc.add_value(
        "priority",
        code="p1",
        account_id=SYSTEM_ACCOUNT_ID,
        as_system=True,
    )
    await db_session.commit()


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
    await _seed_priority_list(svc, db_session)
    return svc


@pytest.mark.asyncio
async def test_codelist_field_accepts_member(service: CodelistService):
    schema = [
        {"name": "priority", "type": "text", "required": True, "codelist": "priority"},
    ]
    errs = await service.validate_record_codelist_fields(
        schema, {"priority": "p1"}, ACCOUNT_A
    )
    assert errs == []


@pytest.mark.asyncio
async def test_codelist_field_rejects_unknown(service: CodelistService):
    schema = [
        {
            "name": "priority",
            "type": "text",
            "options": {"codelist": "priority"},
        },
    ]
    errs = await service.validate_record_codelist_fields(
        schema, {"priority": "nope"}, ACCOUNT_A
    )
    assert len(errs) == 1
    assert errs[0]["code"] == "not_in_codelist"
    assert errs[0]["field"] == "priority"


@pytest.mark.asyncio
async def test_codelist_field_rejects_hidden(service: CodelistService, db_session):
    await service.set_override(
        "priority", "p1", account_id=ACCOUNT_A, visibility="hidden"
    )
    await db_session.commit()
    schema = [{"name": "priority", "type": "text", "codelist": "priority"}]
    errs = await service.validate_record_codelist_fields(
        schema, {"priority": "p1"}, ACCOUNT_A
    )
    assert len(errs) == 1
    assert errs[0]["code"] == "not_in_codelist"
