"""EP-SQLI-*: custom-endpoint aggregate SQL-injection regression guards (C-02).

``_execute_aggregate_records`` interpolates ``collection``, ``group_by`` and
``field`` straight into a ``text()`` statement. Only ``account_id`` is bound as
a parameter, so any of those three identifiers can carry a subquery or a ``--``
comment that detaches the ``WHERE account_id = :account_id`` clause — turning
an account-scoped aggregate into a cross-tenant read.

The values are attacker-reachable at request time because endpoint action
configs support ``{{request.query.*}}`` templating, so an account admin (not a
superadmin) can build an endpoint that reads any other tenant's rows.

The secure behaviour asserted here: injected identifiers must be rejected, or
the aggregate must stay scoped to the caller's own account.

Note: the parser tests in ``tests/integration/test_records_aggregate.py`` and
``test_aggregation_parser.py`` cover the schema-validated record-router path,
which is a *different* code path and does not exercise this executor.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from snackbase.infrastructure.endpoints.endpoint_executor import _execute_aggregate_records
from tests.security.helpers import assert_allowed, assert_no_leak

BETA_MARKER = "BETA-SECRET"
ALPHA_MARKER = "ALPHA-SECRET"


def _session_factory() -> Any:
    """The same session factory the dispatcher hands to the executor."""
    from snackbase.infrastructure.persistence.database import get_db_manager

    return get_db_manager().session


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit level — the executor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(reason="C-02 fix pending", strict=True)
async def test_ep_sqli_001_group_by_subquery_cannot_read_other_tenant(
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-001: a subquery in `group_by` must not surface B's rows."""
    table = two_tenant_collection["table"]

    try:
        result = await _execute_aggregate_records(
            {
                "collection": table,
                "function": "count",
                "group_by": f"(SELECT group_concat(secret) FROM {table})",
            },
            _session_factory(),
            security_test_data["account_a"].id,
        )
    except (ValueError, RuntimeError):
        return  # Rejecting the identifier outright is the preferred outcome.

    assert BETA_MARKER not in str(result), f"cross-tenant leak via group_by: {result}"


@pytest.mark.asyncio
async def test_ep_sqli_002_group_by_comment_cannot_detach_account_filter(
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-002: a `--` comment in `group_by` must not drop the account filter.

    Unlike the subquery form, this payload is already refused: commenting out
    the tail also comments out ``:account_id``, and the driver rejects the
    statement for supplying a binding the SQL no longer uses. That refusal is
    incidental rather than designed, so it is locked in here — a future rewrite
    of the statement builder must not make comment injection viable.
    """
    table = two_tenant_collection["table"]

    try:
        result = await _execute_aggregate_records(
            {
                "collection": table,
                "function": "count",
                "group_by": f"secret FROM {table} --",
            },
            _session_factory(),
            security_test_data["account_a"].id,
        )
    except (ValueError, RuntimeError):
        return

    assert BETA_MARKER not in str(result), f"cross-tenant leak via group_by comment: {result}"


@pytest.mark.asyncio
async def test_ep_sqli_003_collection_identifier_cannot_detach_account_filter(
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-003: an injected `collection` must not widen the row scope.

    The ``WHERE account_id = :account_id`` clause trails the table name, so an
    injected ``collection`` cannot escape the account filter without a comment
    — and comments are refused (see EP-SQLI-002). Locked in as a regression.
    """
    table = two_tenant_collection["table"]

    scoped = await _execute_aggregate_records(
        {"collection": table, "function": "count"},
        _session_factory(),
        security_test_data["account_a"].id,
    )

    try:
        injected = await _execute_aggregate_records(
            {"collection": f"{table} WHERE 1=1 --", "function": "count"},
            _session_factory(),
            security_test_data["account_a"].id,
        )
    except (ValueError, RuntimeError):
        return

    assert injected["value"] <= scoped["value"], (
        f"injected collection widened the scope: {injected} vs {scoped}"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="C-02 fix pending", strict=True)
async def test_ep_sqli_004_field_identifier_cannot_read_other_tenant(
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-004: an injected `field` must not surface B's rows."""
    table = two_tenant_collection["table"]

    try:
        result = await _execute_aggregate_records(
            {
                "collection": table,
                "function": "max",
                "field": f"(SELECT group_concat(secret) FROM {table})",
            },
            _session_factory(),
            security_test_data["account_a"].id,
        )
    except (ValueError, RuntimeError):
        return

    assert BETA_MARKER not in str(result), f"cross-tenant leak via field: {result}"


@pytest.mark.asyncio
async def test_ep_sqli_005_benign_aggregate_stays_account_scoped(
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-005: positive control — a benign aggregate counts only A's rows."""
    result = await _execute_aggregate_records(
        {"collection": two_tenant_collection["table"], "function": "count"},
        _session_factory(),
        security_test_data["account_a"].id,
    )

    assert result["value"] == 1


# ---------------------------------------------------------------------------
# Integration level — the dispatcher, driven by an account admin
# ---------------------------------------------------------------------------


async def _create_leak_endpoint(
    client: AsyncClient, token: str, table: str, path: str
) -> None:
    """Create an endpoint whose aggregate `group_by` comes from the query string."""
    response = await client.post(
        "/api/v1/endpoints",
        json={
            "name": "leak-probe",
            "path": path,
            "method": "GET",
            "auth_required": True,
            "actions": [
                {
                    "type": "aggregate_records",
                    "collection": table,
                    "function": "count",
                    "group_by": "{{request.query.gb}}",
                }
            ],
            "response_template": {
                "status": 200,
                "body": {"result": "{{actions[0].result}}"},
            },
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
@pytest.mark.xfail(reason="C-02 fix pending", strict=True)
async def test_ep_sqli_010_dispatcher_injection_does_not_leak_other_tenant(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-010: an account admin cannot read B's rows through the dispatcher."""
    table = two_tenant_collection["table"]
    account_a = security_test_data["account_a"]
    await _create_leak_endpoint(
        client, security_test_data["user_a_token"], table, "/leak"
    )

    response = await client.get(
        f"/api/v1/x/{account_a.slug}/leak",
        params={"gb": f"(SELECT group_concat(secret) FROM {table})"},
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert_no_leak(response, BETA_MARKER)


@pytest.mark.asyncio
async def test_ep_sqli_011_dispatcher_benign_group_by_positive_control(
    client: AsyncClient,
    security_test_data: dict[str, Any],
    two_tenant_collection: dict[str, Any],
) -> None:
    """EP-SQLI-011: positive control — `gb=secret` returns only A's own value."""
    table = two_tenant_collection["table"]
    account_a = security_test_data["account_a"]
    await _create_leak_endpoint(
        client, security_test_data["user_a_token"], table, "/benign"
    )

    response = await client.get(
        f"/api/v1/x/{account_a.slug}/benign",
        params={"gb": "secret"},
        headers=_auth(security_test_data["user_a_token"]),
    )

    assert_allowed(response, allowed=(200,))
    assert ALPHA_MARKER in response.text
    assert_no_leak(response, BETA_MARKER)
