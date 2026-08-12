"""ISO-ANON-*: anonymous tenant targeting on public collections (M-08).

``_resolve_account_id`` scopes an unauthenticated request by whatever the caller
puts in ``X-Account-ID``, validating only that the account exists. A collection
whose rule was ``""`` (no restriction) was therefore reachable *for every tenant
at once*: the anonymous caller chose which tenant to read from and — with an
empty create rule — which tenant to write into.

Anonymous access now takes two independent allowances, and both have to be
present:

* **The ``allow_anonymous`` opt-in**, per collection, off by default. ``""``
  means "no rule", the natural way to say "no restriction for my users"; it must
  not silently also mean "reachable by the internet". Collections and their
  rules are superadmin-owned, so opening one is an operator's decision, which is
  what makes a public form or public API deliberate rather than incidental.
* **An empty rule for the operation**, unchanged.

Public writes survive the change (``PRD_APP_BUILDER_FOUNDATION.md`` F6.3 built
anonymous access for public forms and landing pages) but only where an operator
has said so.
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


async def _opt_in_to_anonymous(
    client: AsyncClient, superadmin_token: str, collection: str
) -> None:
    """Turn on anonymous reachability for a collection."""
    response = await client.put(
        f"/api/v1/collections/{collection}/rules",
        json={"allow_anonymous": True},
        headers=_auth(superadmin_token),
    )
    assert response.status_code == 200, response.text


@pytest_asyncio.fixture
async def public_collection(
    client: AsyncClient,
    superadmin_token: str,
    security_test_data: dict[str, Any],
) -> dict[str, Any]:
    """A collection with empty (unrestricted) rules, holding one row per tenant.

    Deliberately does *not* set `allow_anonymous`: empty rules alone are exactly
    the configuration that used to be reachable anonymously across every tenant.
    """
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
async def test_iso_anon_001_opted_in_anonymous_read_is_scoped_to_the_header(
    client: AsyncClient,
    superadmin_token: str,
    security_test_data: dict[str, Any],
    public_collection: dict[str, Any],
) -> None:
    """ISO-ANON-001: with the opt-in on, `X-Account-ID` scoping stays honest.

    Originally a characterisation of pre-fix behaviour: it asserted that empty
    rules alone made the collection anonymously readable, which is precisely
    what ISO-ANON-011 requires to be denied. The half worth keeping is that the
    scoping does not leak — choosing A returns A's rows and only A's rows — so
    the collection is opted in here and that is what is asserted. The header is
    resolved by slug or account code, not by account ID.
    """
    collection = public_collection["collection"]
    await _opt_in_to_anonymous(client, superadmin_token, collection)

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
    client: AsyncClient, superadmin_token: str, public_collection: dict[str, Any]
) -> None:
    """ISO-ANON-002: regression — an anonymous request must name a tenant.

    Asserted on an opted-in collection: without the opt-in the answer is 401
    before the header is ever considered, which is the point of ISO-ANON-011.
    """
    collection = public_collection["collection"]
    await _opt_in_to_anonymous(client, superadmin_token, collection)

    response = await client.get(f"/api/v1/records/{collection}")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_iso_anon_003_unknown_account_header_is_rejected(
    client: AsyncClient, superadmin_token: str, public_collection: dict[str, Any]
) -> None:
    """ISO-ANON-003: regression — a non-existent account is not silently accepted."""
    collection = public_collection["collection"]
    await _opt_in_to_anonymous(client, superadmin_token, collection)

    response = await client.get(
        f"/api/v1/records/{collection}",
        headers={"X-Account-ID": "NO0000"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
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
