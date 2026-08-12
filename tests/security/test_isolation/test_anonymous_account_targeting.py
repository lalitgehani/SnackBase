"""ISO-ANON-*: the anonymous access model (M-08, accepted).

``_resolve_account_id`` scopes an unauthenticated request by whatever the caller
puts in ``X-Account-ID``, validating only that the account exists. A collection
whose rule is ``""`` is therefore reachable anonymously *for every tenant at
once*: the caller chooses which tenant to read from and, with an empty create
rule, which one to write into.

**M-08 is accepted rather than fixed.** The VAPT asked for a separate
per-collection opt-in on top of the rule, and that was built and then reverted:
it added no authorization the rules did not already have. ``""`` is the
documented "no rule" value, an expression such as ``@request.auth.id != ""``
already means "authenticated callers only, no row restriction", and both the
rules and the flag are superadmin-owned — so the flag moved no decision and
closed no gap, while duplicating the control. Anonymous reachability therefore
stays a property of the rules alone, as designed in
``PRD_APP_BUILDER_FOUNDATION.md`` F6.3 (public forms, landing pages, public
APIs).

What that leaves standing, and what these tests pin down:

* An empty rule means the collection is reachable by anyone, in whichever tenant
  the header names. Setting one is a deliberate superadmin act.
* Because collections and their rules are global, opening one opens it for every
  account holding rows in it. Tenant admins cannot set rules and so cannot
  consent — the residual risk of the model.
* Scoping is still honest: a caller naming account A sees only A's rows, so this
  is a reachability decision and not a cross-tenant leak.

The two guards that asserted the opt-in (``ISO-ANON-010/011``) were removed with
the flag; asserting a control that was deliberately not built is not a guard, it
is a permanently failing test.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

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
async def test_iso_anon_001_anonymous_read_is_scoped_to_the_named_tenant(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    public_collection: dict[str, Any],
) -> None:
    """ISO-ANON-001: `X-Account-ID` picks the tenant scope, and only that scope.

    An empty rule is what makes this collection anonymously reachable, and the
    header decides which account's rows the caller sees. The guard is that the
    scoping holds: choosing A returns A's rows and none of B's, so the exposure
    is the reachability the rule asked for and not a cross-tenant leak.

    The header is resolved by slug or account code, not by account ID.
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
