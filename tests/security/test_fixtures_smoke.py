"""Smoke tests for the two-tenant per-surface fixtures (F1.1).

These assert the harness itself is sound *before* any attack test relies on it:
each fixture yields its documented keys, and the owning tenant can reach its own
resource. A fixture that silently produced nothing would make every later
cross-tenant assertion pass vacuously.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.security.helpers import assert_allowed


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_two_tenant_files_yields_account_scoped_paths(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_files: dict[str, Any],
) -> None:
    """Paths are account-prefixed, exist on disk, and download for their owner."""
    account_a = security_test_data["account_a"]
    account_b = security_test_data["account_b"]
    storage_root = two_tenant_files["storage_root"]

    assert two_tenant_files["account_a_path"].startswith(f"{account_a.id}/")
    assert two_tenant_files["account_b_path"].startswith(f"{account_b.id}/")

    assert (storage_root / two_tenant_files["account_a_path"]).exists()
    assert (storage_root / two_tenant_files["account_b_path"]).exists()

    response = await client.get(
        f"/api/v1/files/{two_tenant_files['account_a_path']}",
        headers=_auth(security_test_data["user_a_token"]),
    )
    assert_allowed(response, allowed=(200,))
    assert two_tenant_files["account_a_marker"] in response.text


@pytest.mark.asyncio
async def test_two_tenant_collection_isolation_holds_before_attacks(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """A plain list as user A returns exactly the A-owned record."""
    assert two_tenant_collection["account_a_record_id"]
    assert two_tenant_collection["account_b_record_id"]

    response = await client.get(
        f"/api/v1/records/{two_tenant_collection['collection']}",
        headers=_auth(security_test_data["user_a_token"]),
    )
    assert_allowed(response, allowed=(200,))

    items = response.json()["items"]
    assert [item["id"] for item in items] == [two_tenant_collection["account_a_record_id"]]
    assert two_tenant_collection["account_b_marker"] not in response.text


@pytest.mark.asyncio
async def test_two_tenant_endpoints_dispatch_for_owning_tenant(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_endpoints: dict[str, Any],
) -> None:
    """Each dispatcher URL returns 200 for its owning tenant's token."""
    assert two_tenant_endpoints["account_a_id"]
    assert two_tenant_endpoints["account_b_id"]

    response_a = await client.get(
        two_tenant_endpoints["account_a_url"],
        headers=_auth(security_test_data["user_a_token"]),
    )
    assert_allowed(response_a, allowed=(200,))
    assert two_tenant_endpoints["account_a_marker"] in response_a.text

    response_b = await client.get(
        two_tenant_endpoints["account_b_url"],
        headers=_auth(security_test_data["user_b_token"]),
    )
    assert_allowed(response_b, allowed=(200,))
    assert two_tenant_endpoints["account_b_marker"] in response_b.text


@pytest.mark.asyncio
async def test_two_tenant_functions_yields_owner_readable_functions(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_functions: dict[str, Any],
) -> None:
    """Each function is readable by its owning tenant (or the fixture skipped)."""
    response = await client.get(
        two_tenant_functions["account_a_url"],
        headers=_auth(security_test_data["user_a_token"]),
    )
    assert_allowed(response, allowed=(200,))
    assert response.json()["slug"] == two_tenant_functions["account_a_slug"]

    response_b = await client.get(
        two_tenant_functions["account_b_url"],
        headers=_auth(security_test_data["admin_b_token"]),
    )
    assert_allowed(response_b, allowed=(200,))
    assert response_b.json()["slug"] == two_tenant_functions["account_b_slug"]
