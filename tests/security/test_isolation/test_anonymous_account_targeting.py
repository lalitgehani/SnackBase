"""ISO-ANON-*: anonymous tenant targeting on public collections (M-08).

``_resolve_account_id`` scopes an unauthenticated request by whatever the
caller puts in ``X-Account-ID``, validating only that the account exists. Any
collection whose rule is ``""`` (public) is therefore public *for every tenant
at once*: the anonymous caller chooses which tenant to read from, and — for a
public create rule — which tenant to write into.

Two things are missing:

* **Per-collection opt-in.** ``""`` means "no rule", which is the natural way
  to express "no restriction for my users". It should not silently also mean
  "reachable by the internet across every tenant".
* **Write attribution.** An anonymous create currently lands in whichever
  account the header names, so a caller can plant records in a tenant they have
  no relationship with.

The first test characterises today's behaviour so the change is deliberate and
visible; the rest assert the target model.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.security.helpers import assert_denied

ALPHA_MARKER = "ALPHA-PUBLIC-ROW"
BETA_MARKER = "BETA-PUBLIC-ROW"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def public_collection(
    client: AsyncClient,
    superadmin_token: str,
    security_test_data: dict[str, Any],
) -> dict[str, Any]:
    """A fully public collection holding one row per tenant."""
    name = f"public_{uuid.uuid4().hex[:8]}"
    admin_headers = _auth(superadmin_token)

    created = await client.post(
        "/api/v1/collections",
        json={
            "name": name,
            "schema": [{"name": "title", "type": "text", "required": True}],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text

    rules = await client.put(
        f"/api/v1/collections/{name}/rules",
        json={"list_rule": "", "view_rule": "", "create_rule": ""},
        headers=admin_headers,
    )
    assert rules.status_code == 200, rules.text

    for token, marker in (
        (security_test_data["user_a_token"], ALPHA_MARKER),
        (security_test_data["user_b_token"], BETA_MARKER),
    ):
        seeded = await client.post(
            f"/api/v1/records/{name}", json={"title": marker}, headers=_auth(token)
        )
        assert seeded.status_code == 201, seeded.text

    return {"collection": name}


@pytest.mark.asyncio
async def test_iso_anon_001_characterisation_anonymous_selects_tenant(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    public_collection: dict[str, Any],
) -> None:
    """ISO-ANON-001: characterisation — `X-Account-ID` picks the tenant scope.

    The header is resolved by slug or account code, not by account ID.

    Documents current behaviour so the hardening below is an intentional
    change, not an accidental regression. It also shows the scoping itself is
    honest: choosing A returns only A's rows.
    """
    collection = public_collection["collection"]

    as_a = await client.get(
        f"/api/v1/records/{collection}",
        headers={"X-Account-ID": security_test_data["account_a"].slug},
    )
    as_b = await client.get(
        f"/api/v1/records/{collection}",
        headers={"X-Account-ID": security_test_data["account_b"].slug},
    )

    assert as_a.status_code == 200, as_a.text
    assert as_b.status_code == 200, as_b.text
    assert ALPHA_MARKER in as_a.text and BETA_MARKER not in as_a.text
    assert BETA_MARKER in as_b.text and ALPHA_MARKER not in as_b.text


@pytest.mark.asyncio
async def test_iso_anon_002_anonymous_request_without_header_is_rejected(
    client: AsyncClient, public_collection: dict[str, Any]
) -> None:
    """ISO-ANON-002: regression — an anonymous request must name a tenant."""
    response = await client.get(f"/api/v1/records/{public_collection['collection']}")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_iso_anon_003_unknown_account_header_is_rejected(
    client: AsyncClient, public_collection: dict[str, Any]
) -> None:
    """ISO-ANON-003: regression — a non-existent account is not silently accepted."""
    response = await client.get(
        f"/api/v1/records/{public_collection['collection']}",
        headers={"X-Account-ID": "NO0000"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-08 fix pending", strict=True)
async def test_iso_anon_010_anonymous_write_cannot_attribute_to_a_chosen_account(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    public_collection: dict[str, Any],
) -> None:
    """ISO-ANON-010: an anonymous create must not land in an arbitrary tenant."""
    response = await client.post(
        f"/api/v1/records/{public_collection['collection']}",
        json={"title": "PLANTED-BY-ANONYMOUS"},
        headers={"X-Account-ID": security_test_data["account_a"].slug},
    )

    assert_denied(response, allowed=(400, 401, 403))


@pytest.mark.asyncio
@pytest.mark.xfail(reason="M-08 fix pending", strict=True)
async def test_iso_anon_011_public_access_requires_explicit_opt_in(
    client: AsyncClient,
    superadmin_token: str,
    security_test_data: dict[str, Any],
    public_collection: dict[str, Any],
) -> None:
    """ISO-ANON-011: an empty rule alone must not expose a collection anonymously.

    Anonymous reachability should require a deliberate per-collection flag, so
    "no rule for my users" cannot be mistaken for "open to the internet".
    """
    response = await client.get(
        f"/api/v1/records/{public_collection['collection']}",
        headers={"X-Account-ID": security_test_data["account_a"].slug},
    )

    assert_denied(response, allowed=(401, 403), leak_markers=(ALPHA_MARKER,))
