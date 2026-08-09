"""FN-ISO-*: cross-tenant isolation for functions (F4.5).

The same A→B matrix the record router already enjoys, applied to the functions
management surface: read, update, delete, invoke, secrets, and creation-time
account forgery.

This is the *management* boundary only — the host-level sandbox gaps live in
``test_sandbox_isolation.py`` (FN-SBX-*, C-04).
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from tests.security.conftest import AttackClient
from tests.security.helpers import (
    OWNER_CONTROL_KEY,
    assert_allowed,
    assert_denied,
    assert_no_leak,
    cross_tenant_matrix,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_fn_iso_001_cross_tenant_matrix_on_function_management(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """FN-ISO-001: B cannot read, update or delete A's function by slug."""
    results = await cross_tenant_matrix(
        attack_client,
        victim_url=two_tenant_functions["account_a_url"],
        victim_token=security_test_data["user_a_token"],
        attacker_token=security_test_data["admin_b_token"],
        write_body={"name": "hijacked"},
    )

    assert_allowed(results[OWNER_CONTROL_KEY], allowed=(200,))
    for method in ("GET", "PATCH", "DELETE"):
        assert_denied(
            results[method],
            allowed=(403, 404, 405),
            leak_markers=(two_tenant_functions["account_a_slug"],),
        )


@pytest.mark.asyncio
async def test_fn_iso_002_function_survives_cross_tenant_delete(
    client: AsyncClient,
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """FN-ISO-002: a denied DELETE must not have removed the function anyway."""
    await attack_client.delete(
        two_tenant_functions["account_a_url"],
        headers=_auth(security_test_data["admin_b_token"]),
        description="B attempts to delete A's function",
    )

    still_there = await client.get(
        two_tenant_functions["account_a_url"],
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert_allowed(still_there, allowed=(200,))


@pytest.mark.asyncio
async def test_fn_iso_003_listing_never_includes_other_tenants_functions(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """FN-ISO-003: the function list is scoped to the caller's account."""
    response = await attack_client.get(
        "/api/v1/functions",
        headers=_auth(security_test_data["admin_b_token"]),
        description="B lists functions",
    )

    assert_allowed(response, allowed=(200,))
    assert_no_leak(response, two_tenant_functions["account_a_slug"])


@pytest.mark.asyncio
async def test_fn_iso_004_cannot_read_other_tenants_function_body(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """FN-ISO-004: source code is not readable across tenants."""
    response = await attack_client.get(
        f"{two_tenant_functions['account_a_url']}/body",
        headers=_auth(security_test_data["admin_b_token"]),
        description="B reads A's function source",
    )

    assert_denied(response, allowed=(403, 404))


@pytest.mark.asyncio
async def test_fn_iso_005_cannot_invoke_other_tenants_function(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """FN-ISO-005: B cannot invoke A's function through the dispatcher."""
    account_a = security_test_data["account_a"]

    response = await attack_client.post(
        f"/api/v1/f/{account_a.slug}/{two_tenant_functions['account_a_slug']}",
        json={},
        headers=_auth(security_test_data["admin_b_token"]),
        description="B invokes A's function",
    )

    assert_denied(response, allowed=(401, 403, 404))


@pytest.mark.asyncio
async def test_fn_iso_006_forged_account_on_create_is_ignored(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """FN-ISO-006: a forged account on create must not attribute to another tenant."""
    account_a = security_test_data["account_a"]
    account_b = security_test_data["account_b"]

    response = await client.post(
        "/api/v1/functions",
        json={
            "name": "forged",
            "slug": "forged-owner",
            "account_id": account_a.id,
        },
        headers={
            **_auth(security_test_data["admin_b_token"]),
            "X-Account-ID": account_a.id,
        },
    )

    assert response.status_code in (201, 422), response.text
    if response.status_code == 201:
        assert response.json()["account_id"] == account_b.id, (
            "a forged account_id/X-Account-ID attributed the function to another tenant"
        )
