"""EP-ISO-*: cross-tenant isolation for custom endpoints (F4.5).

The record router has had the full six-check isolation discipline for a while
(``tests/security/test_isolation/test_account_isolation.py``). Custom endpoints
are a newer surface carrying the same kind of tenant-owned resource, so they get
the same A→B matrix: read, update, delete, invoke, and creation-time account
forgery.
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
async def test_ep_iso_001_cross_tenant_matrix_on_endpoint_management(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """EP-ISO-001: B cannot read, update or delete A's endpoint by ID."""
    results = await cross_tenant_matrix(
        attack_client,
        victim_url=f"/api/v1/endpoints/{two_tenant_endpoints['account_a_id']}",
        victim_token=security_test_data["user_a_token"],
        attacker_token=security_test_data["user_b_token"],
    )

    assert_allowed(results[OWNER_CONTROL_KEY], allowed=(200,))
    for method in ("GET", "PATCH", "DELETE"):
        assert_denied(
            results[method],
            allowed=(403, 404, 405),
            leak_markers=(two_tenant_endpoints["account_a_marker"],),
        )


@pytest.mark.asyncio
async def test_ep_iso_002_endpoint_still_exists_after_cross_tenant_delete(
    client: AsyncClient,
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """EP-ISO-002: a denied DELETE must not have removed the resource anyway."""
    await attack_client.delete(
        f"/api/v1/endpoints/{two_tenant_endpoints['account_a_id']}",
        headers=_auth(security_test_data["user_b_token"]),
        description="B attempts to delete A's endpoint",
    )

    still_there = await client.get(
        f"/api/v1/endpoints/{two_tenant_endpoints['account_a_id']}",
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert_allowed(still_there, allowed=(200,))


@pytest.mark.asyncio
async def test_ep_iso_003_cannot_invoke_other_tenants_dispatcher_path(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """EP-ISO-003: B's token cannot invoke A's endpoint through the dispatcher."""
    response = await attack_client.get(
        two_tenant_endpoints["account_a_url"],
        headers=_auth(security_test_data["user_b_token"]),
        description="B invokes A's custom endpoint",
    )

    assert_denied(
        response,
        allowed=(401, 403, 404),
        leak_markers=(two_tenant_endpoints["account_a_marker"],),
    )


@pytest.mark.asyncio
async def test_ep_iso_004_forged_account_id_on_create_is_ignored(
    client: AsyncClient, security_test_data: dict[str, Any]
) -> None:
    """EP-ISO-004: a forged account on create must not attribute to another tenant."""
    account_a = security_test_data["account_a"]
    account_b = security_test_data["account_b"]

    response = await client.post(
        "/api/v1/endpoints",
        json={
            "name": "forged",
            "path": "/forged-owner",
            "method": "GET",
            "account_id": account_a.id,
            "actions": [],
        },
        headers={
            **_auth(security_test_data["user_b_token"]),
            "X-Account-ID": account_a.id,
        },
    )

    assert response.status_code in (201, 422), response.text
    if response.status_code == 201:
        assert response.json()["account_id"] == account_b.id, (
            "a forged account_id/X-Account-ID attributed the endpoint to another tenant"
        )


@pytest.mark.asyncio
async def test_ep_iso_005_listing_never_includes_other_tenants_endpoints(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """EP-ISO-005: the list endpoint is scoped to the caller's account."""
    response = await attack_client.get(
        "/api/v1/endpoints",
        headers=_auth(security_test_data["user_b_token"]),
        description="B lists endpoints",
    )

    assert_allowed(response, allowed=(200,))
    assert_no_leak(response, two_tenant_endpoints["account_a_id"])
    assert_no_leak(response, two_tenant_endpoints["account_a_marker"])


@pytest.mark.asyncio
async def test_ep_iso_006_cannot_read_other_tenants_execution_history(
    attack_client: AttackClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """EP-ISO-006: execution history is not readable across tenants."""
    response = await attack_client.get(
        f"/api/v1/endpoints/{two_tenant_endpoints['account_a_id']}/executions",
        headers=_auth(security_test_data["user_b_token"]),
        description="B reads A's endpoint execution history",
    )

    assert_denied(response, allowed=(403, 404))
