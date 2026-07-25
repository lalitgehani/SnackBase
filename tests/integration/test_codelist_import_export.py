"""Import/export round-trip and inactive historical semantics (Phase 5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.codelist_service import (
    CodelistService,
    CodelistValidationError,
)
from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.repositories.codelist_repository import (
    SYSTEM_ACCOUNT_ID,
)

ACCOUNT_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"


@pytest.mark.asyncio
async def test_export_import_roundtrip_superadmin(
    client: AsyncClient, superadmin_token: str
):
    # Create system list with labels
    r = await client.post(
        "/api/v1/codelists",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"code": "pkg_demo", "name": "Package Demo", "scope": "system"},
    )
    assert r.status_code == 201, r.text
    await client.post(
        "/api/v1/codelists/pkg_demo/manage/values",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "code": "a1",
            "labels": [
                {"language": "en", "label": "Alpha"},
                {"language": "ja", "label": "アルファ"},
            ],
        },
    )
    exp = await client.get(
        "/api/v1/codelists/pkg_demo/export",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    assert exp.status_code == 200, exp.text
    package = exp.json()
    assert package["format"] == "snackbase.codelist"
    assert package["format_version"] == "1.0"
    assert package["codelist"]["code"] == "pkg_demo"
    assert any(v["code"] == "a1" for v in package["values"])

    # Deactivate original then re-import (idempotent upsert)
    await client.delete(
        "/api/v1/codelists/pkg_demo",
        headers={"Authorization": f"Bearer {superadmin_token}"},
    )
    imp = await client.post(
        "/api/v1/codelists/import",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"package": package},
    )
    assert imp.status_code == 201, imp.text
    assert imp.json()["code"] == "pkg_demo"

    # Invalid package rejected
    bad = await client.post(
        "/api/v1/codelists/import",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"package": {"format": "nope"}},
    )
    assert bad.status_code in (400, 422)


@pytest.mark.asyncio
async def test_inactive_excluded_from_picker_but_label_resolvable(
    db_session: AsyncSession,
):
    if await db_session.get(AccountModel, ACCOUNT_A) is None:
        db_session.add(
            AccountModel(
                id=ACCOUNT_A,
                account_code="CC0001",
                slug="acct-cc",
                name="CC",
            )
        )
        await db_session.commit()

    svc = CodelistService(db_session)
    await svc.create_codelist(
        code="hist_list",
        name="Historical",
        account_id=SYSTEM_ACCOUNT_ID,
        scope="system",
    )
    v = await svc.add_value(
        "hist_list",
        code="old",
        account_id=SYSTEM_ACCOUNT_ID,
        as_system=True,
    )
    await svc.set_label(v.id, "en", "Old Label")
    await db_session.commit()

    await svc.deactivate_value(
        "hist_list", "old", account_id=SYSTEM_ACCOUNT_ID
    )
    await db_session.commit()

    effective = await svc.get_effective_values(ACCOUNT_A, "hist_list", "en")
    assert "old" not in {e.code for e in effective}

    with pytest.raises(CodelistValidationError):
        await svc.assert_in_codelist(ACCOUNT_A, "hist_list", "old")

    ok = await svc.assert_in_codelist(
        ACCOUNT_A, "hist_list", "old", allow_inactive_existing=True
    )
    assert ok.code == "old"

    label = await svc.resolve_label(
        "hist_list", "old", "en", account_id=ACCOUNT_A, include_inactive=True
    )
    assert label == "Old Label"
