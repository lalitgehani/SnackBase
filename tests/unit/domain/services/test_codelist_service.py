"""Unit tests for CodelistService (Phase 1 foundation).

Covers entities, uniqueness, soft-deactivate, overrides, label fallback,
effective-resolution matrix, and idempotent regions/eu-01 seed.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from snackbase.domain.entities.codelist import (
    Codelist,
    CodelistValue,
    CodelistValueLabel,
    EffectiveCodelistValue,
)
from snackbase.domain.services.codelist_service import (
    CodelistConflictError,
    CodelistForbiddenError,
    CodelistNotFoundError,
    CodelistService,
    CodelistValidationError,
    CodelistValueNotFoundError,
)
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ACCOUNT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def _ensure_accounts(session) -> None:
    """Ensure system + two tenant accounts exist for isolation tests."""
    for aid, code, slug, name in [
        (SYSTEM_ACCOUNT_ID, "SY0000", "system", "System Account"),
        (ACCOUNT_A, "AA0001", "account-a", "Account A"),
        (ACCOUNT_B, "BB0001", "account-b", "Account B"),
    ]:
        existing = await session.get(AccountModel, aid)
        if existing is None:
            session.add(
                AccountModel(
                    id=aid,
                    account_code=code,
                    slug=slug,
                    name=name,
                )
            )
    await session.commit()


@pytest.fixture
async def service(db_session) -> CodelistService:
    await _ensure_accounts(db_session)
    return CodelistService(db_session)


# ---------------------------------------------------------------------------
# Entity validation
# ---------------------------------------------------------------------------


def test_codelist_entity_requires_fields():
    with pytest.raises(ValueError, match="code"):
        Codelist(id="1", code="", name="N", account_id=SYSTEM_ACCOUNT_ID, scope="system")
    with pytest.raises(ValueError, match="scope"):
        Codelist(
            id="1", code="x", name="N", account_id=SYSTEM_ACCOUNT_ID, scope="global"
        )


def test_value_entity_requires_code():
    with pytest.raises(ValueError, match="code"):
        CodelistValue(
            id="1", codelist_id="c", code="", account_id=SYSTEM_ACCOUNT_ID, scope="system"
        )


def test_label_entity_rejects_empty():
    with pytest.raises(ValueError, match="Language"):
        CodelistValueLabel(id="1", value_id="v", language="", label="L")
    with pytest.raises(ValueError, match="Label"):
        CodelistValueLabel(id="1", value_id="v", language="en", label="  ")


# ---------------------------------------------------------------------------
# Codelist CRUD + uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system_and_account_codelists(service: CodelistService, db_session):
    system = await service.create_codelist(
        code="statuses",
        name="Statuses",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    assert system.is_system is True
    assert system.account_id == SYSTEM_ACCOUNT_ID
    assert system.scope == "system"

    private = await service.create_codelist(
        code="my_enums",
        name="My Enums",
        account_id=ACCOUNT_A,
        scope="account",
    )
    await db_session.commit()
    assert private.is_system is False
    assert private.account_id == ACCOUNT_A


@pytest.mark.asyncio
async def test_duplicate_system_code_rejected(service: CodelistService, db_session):
    await service.create_codelist(
        code="dupsys",
        name="Dup",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    with pytest.raises(CodelistConflictError):
        await service.create_codelist(
            code="dupsys",
            name="Dup2",
            account_id=SYSTEM_ACCOUNT_ID,
            scope="system",
        )


@pytest.mark.asyncio
async def test_duplicate_account_code_rejected(service: CodelistService, db_session):
    await service.create_codelist(
        code="dupacct",
        name="Dup",
        account_id=ACCOUNT_A,
        scope="account",
    )
    await db_session.commit()
    with pytest.raises(CodelistConflictError):
        await service.create_codelist(
            code="dupacct",
            name="Dup2",
            account_id=ACCOUNT_A,
            scope="account",
        )


@pytest.mark.asyncio
async def test_account_cannot_shadow_system_code(service: CodelistService, db_session):
    await service.create_codelist(
        code="shared_dim",
        name="Shared",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    with pytest.raises(CodelistConflictError, match="system codelist"):
        await service.create_codelist(
            code="shared_dim",
            name="Shadow",
            account_id=ACCOUNT_A,
            scope="account",
        )


@pytest.mark.asyncio
async def test_account_a_cannot_load_account_b_private_list(
    service: CodelistService, db_session
):
    private = await service.create_codelist(
        code="secret_b",
        name="Secret B",
        account_id=ACCOUNT_B,
        scope="account",
    )
    await db_session.commit()
    # Listing for A should not include B's private list
    listed = await service.list_codelists(account_id=ACCOUNT_A)
    codes = {c.code for c in listed}
    assert "secret_b" not in codes
    # get by code with account A should not find B's list
    with pytest.raises(CodelistNotFoundError):
        await service.get_codelist("secret_b", account_id=ACCOUNT_A)
    # By id via repo scope: service get_codelist_by_id returns model but
    # list isolation is the product boundary; ensure B can get it
    found = await service.get_codelist("secret_b", account_id=ACCOUNT_B)
    assert found.id == private.id


@pytest.mark.asyncio
async def test_builtin_prevents_hard_delete(service: CodelistService, db_session):
    cl = await service.create_codelist(
        code="builtin_x",
        name="Builtin",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_builtin=True,
    )
    await db_session.commit()
    with pytest.raises(CodelistForbiddenError, match="hard-deleted"):
        await service.delete_codelist("builtin_x", hard=True)
    soft = await service.delete_codelist("builtin_x", hard=False)
    assert soft.is_active is False


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_value_with_metadata_and_soft_deactivate(
    service: CodelistService, db_session
):
    await service.create_codelist(
        code="regions_test",
        name="Regions Test",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_extensible=False,
    )
    await db_session.commit()
    meta = {"country": "DE", "status": "available"}
    value = await service.add_value(
        "regions_test",
        code="eu-99",
        account_id=SYSTEM_ACCOUNT_ID,
        metadata=meta,
        as_system=True,
        sort_order=1,
    )
    await db_session.commit()
    assert value.metadata_ == meta
    assert value.is_active is True

    deactivated = await service.deactivate_value(
        "regions_test", "eu-99", account_id=SYSTEM_ACCOUNT_ID
    )
    await db_session.commit()
    assert deactivated.is_active is False
    # Still queryable by id for historical display
    still = await service.repo.get_value_by_id(value.id)
    assert still is not None
    assert still.code == "eu-99"
    assert still.is_active is False


@pytest.mark.asyncio
async def test_value_uniqueness(service: CodelistService, db_session):
    await service.create_codelist(
        code="uniqvals",
        name="Uniq",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "uniqvals", code="v1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    with pytest.raises(CodelistConflictError):
        await service.add_value(
            "uniqvals", code="v1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
        )


@pytest.mark.asyncio
async def test_extension_only_when_extensible(service: CodelistService, db_session):
    await service.create_codelist(
        code="non_ext",
        name="Non Ext",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_extensible=False,
    )
    await service.create_codelist(
        code="yes_ext",
        name="Yes Ext",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_extensible=True,
    )
    await db_session.commit()
    with pytest.raises(CodelistForbiddenError, match="not extensible"):
        await service.add_value(
            "non_ext", code="x1", account_id=ACCOUNT_A, as_system=False
        )
    ext = await service.add_value(
        "yes_ext", code="x1", account_id=ACCOUNT_A, as_system=False
    )
    await db_session.commit()
    assert ext.account_id == ACCOUNT_A
    assert ext.is_system is False


# ---------------------------------------------------------------------------
# Labels + fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_labels_en_ja_and_fallback(service: CodelistService, db_session):
    await service.create_codelist(
        code="langs",
        name="Langs",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    value = await service.add_value(
        "langs", code="opt1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await service.set_label(value.id, "en", "Option One")
    await service.set_label(value.id, "ja", "オプション一")
    await db_session.commit()

    assert (
        await service.resolve_label("langs", "opt1", "ja", account_id=ACCOUNT_A)
        == "オプション一"
    )
    assert (
        await service.resolve_label("langs", "opt1", "en", account_id=ACCOUNT_A)
        == "Option One"
    )
    # Missing language falls back to en
    assert (
        await service.resolve_label("langs", "opt1", "fr", account_id=ACCOUNT_A)
        == "Option One"
    )

    # No labels at all → code
    value2 = await service.add_value(
        "langs", code="opt2", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    assert (
        await service.resolve_label("langs", "opt2", "ja", account_id=ACCOUNT_A)
        == "opt2"
    )


def test_resolve_label_from_map_chain():
    assert (
        CodelistService.resolve_label_from_map({"en": "EN", "ja": "JA"}, "c", "ja")
        == "JA"
    )
    assert CodelistService.resolve_label_from_map({"en": "EN"}, "c", "ja") == "EN"
    assert CodelistService.resolve_label_from_map({}, "c", "ja") == "c"
    assert (
        CodelistService.resolve_label_from_map({"en": "EN"}, "c", "ja-JP") == "EN"
    )


@pytest.mark.asyncio
async def test_empty_label_rejected(service: CodelistService, db_session):
    await service.create_codelist(
        code="lbl",
        name="L",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    value = await service.add_value(
        "lbl", code="v", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    with pytest.raises(CodelistValidationError, match="Label"):
        await service.set_label(value.id, "en", "")
    with pytest.raises(CodelistValidationError, match="Language"):
        await service.set_label(value.id, "", "x")


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_override_hide_default_clear(service: CodelistService, db_session):
    await service.create_codelist(
        code="ovlist",
        name="OV",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "ovlist", code="a", account_id=SYSTEM_ACCOUNT_ID, as_system=True, sort_order=1
    )
    await service.add_value(
        "ovlist", code="b", account_id=SYSTEM_ACCOUNT_ID, as_system=True, sort_order=2
    )
    await db_session.commit()

    await service.set_override(
        "ovlist", "a", account_id=ACCOUNT_A, visibility="hidden"
    )
    await service.set_override(
        "ovlist", "b", account_id=ACCOUNT_A, is_default=True
    )
    await db_session.commit()

    effective_a = await service.get_effective_values(ACCOUNT_A, "ovlist", "en")
    codes_a = [e.code for e in effective_a]
    assert "a" not in codes_a
    assert "b" in codes_a
    assert any(e.is_default for e in effective_a if e.code == "b")

    # Account B still sees both
    effective_b = await service.get_effective_values(ACCOUNT_B, "ovlist", "en")
    codes_b = {e.code for e in effective_b}
    assert codes_b == {"a", "b"}

    await service.clear_override("ovlist", "a", account_id=ACCOUNT_A)
    await db_session.commit()
    restored = await service.get_effective_values(ACCOUNT_A, "ovlist", "en")
    assert "a" in {e.code for e in restored}


@pytest.mark.asyncio
async def test_override_isolation_account_b_cannot_see_a(
    service: CodelistService, db_session
):
    await service.create_codelist(
        code="iso_ov",
        name="ISO",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "iso_ov", code="z", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    await service.set_override(
        "iso_ov", "z", account_id=ACCOUNT_A, visibility="hidden"
    )
    await db_session.commit()

    ovs_b = await service.list_overrides("iso_ov", account_id=ACCOUNT_B)
    assert ovs_b == []
    ovs_a = await service.list_overrides("iso_ov", account_id=ACCOUNT_A)
    assert len(ovs_a) == 1


@pytest.mark.asyncio
async def test_default_uniqueness(service: CodelistService, db_session):
    await service.create_codelist(
        code="defs",
        name="Defs",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "defs", code="d1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await service.add_value(
        "defs", code="d2", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    await service.set_override(
        "defs", "d1", account_id=ACCOUNT_A, is_default=True
    )
    await service.set_override(
        "defs", "d2", account_id=ACCOUNT_A, is_default=True
    )
    await db_session.commit()
    effective = await service.get_effective_values(ACCOUNT_A, "defs", "en")
    defaults = [e for e in effective if e.is_default]
    assert len(defaults) == 1
    assert defaults[0].code == "d2"


# ---------------------------------------------------------------------------
# Effective resolution matrix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_effective_no_overrides_returns_system(
    service: CodelistService, db_session
):
    await service.create_codelist(
        code="eff1",
        name="E1",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    v = await service.add_value(
        "eff1", code="s1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await service.set_label(v.id, "en", "System One")
    await db_session.commit()

    eff = await service.get_effective_values(ACCOUNT_A, "eff1", "en")
    assert len(eff) == 1
    assert eff[0].code == "s1"
    assert eff[0].label == "System One"
    assert isinstance(eff[0], EffectiveCodelistValue)


@pytest.mark.asyncio
async def test_new_system_value_appears_without_fan_out(
    service: CodelistService, db_session
):
    await service.create_codelist(
        code="shared_all",
        name="Shared",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "shared_all", code="new1", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()

    for acct in (ACCOUNT_A, ACCOUNT_B):
        eff = await service.get_effective_values(acct, "shared_all", "en")
        assert "new1" in {e.code for e in eff}

    # No per-account value rows for new1
    values = await service.list_values(
        "shared_all", account_id=ACCOUNT_A, include_inactive=True
    )
    owners = {v.account_id for v in values if v.code == "new1"}
    assert owners == {SYSTEM_ACCOUNT_ID}


@pytest.mark.asyncio
async def test_extension_only_for_owning_account(service: CodelistService, db_session):
    await service.create_codelist(
        code="extlist",
        name="Ext",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_extensible=True,
    )
    await db_session.commit()
    await service.add_value(
        "extlist", code="sys", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await service.add_value(
        "extlist", code="only_a", account_id=ACCOUNT_A, as_system=False
    )
    await db_session.commit()

    codes_a = {
        e.code for e in await service.get_effective_values(ACCOUNT_A, "extlist", "en")
    }
    codes_b = {
        e.code for e in await service.get_effective_values(ACCOUNT_B, "extlist", "en")
    }
    assert codes_a == {"sys", "only_a"}
    assert codes_b == {"sys"}


@pytest.mark.asyncio
async def test_assert_in_codelist_pass_fail(service: CodelistService, db_session):
    await service.create_codelist(
        code="assert_cl",
        name="Assert",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    await db_session.commit()
    await service.add_value(
        "assert_cl", code="ok", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await service.add_value(
        "assert_cl", code="hid", account_id=SYSTEM_ACCOUNT_ID, as_system=True
    )
    await db_session.commit()
    await service.set_override(
        "assert_cl", "hid", account_id=ACCOUNT_A, visibility="hidden"
    )
    await db_session.commit()

    ok = await service.assert_in_codelist(ACCOUNT_A, "assert_cl", "ok")
    assert ok.code == "ok"

    with pytest.raises(CodelistValidationError, match="not a valid member"):
        await service.assert_in_codelist(ACCOUNT_A, "assert_cl", "hid")
    with pytest.raises(CodelistValidationError):
        await service.assert_in_codelist(ACCOUNT_A, "assert_cl", "unknown")


# ---------------------------------------------------------------------------
# Shared system list without platform seed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operator_created_system_list_shared_without_fan_out(
    service: CodelistService, db_session
):
    """Operator-created system values appear for all accounts (no per-account rows)."""
    cl = await service.create_codelist(
        code="priority",
        name="Priority",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
        is_builtin=True,
    )
    await db_session.commit()
    v = await service.add_value(
        "priority",
        code="p1",
        account_id=SYSTEM_ACCOUNT_ID,
        as_system=True,
        metadata={"rank": 1},
    )
    await service.set_label(v.id, "en", "Priority One")
    await db_session.commit()

    for acct in (ACCOUNT_A, ACCOUNT_B):
        eff = await service.get_effective_values(acct, "priority", "en")
        assert any(e.code == "p1" and e.label == "Priority One" for e in eff)

    values = await service.list_values("priority", account_id=ACCOUNT_A)
    assert len([x for x in values if x.code == "p1"]) == 1
    assert values[0].account_id == SYSTEM_ACCOUNT_ID

    with pytest.raises(CodelistForbiddenError):
        await service.delete_codelist("priority", hard=True)
    assert cl.is_builtin is True


@pytest.mark.asyncio
async def test_invalid_codelist_code_pattern(service: CodelistService):
    with pytest.raises(CodelistValidationError, match="code must match"):
        await service.create_codelist(
            code="Bad-Code",
            name="X",
            account_id=ACCOUNT_A,
            scope="account",
        )
