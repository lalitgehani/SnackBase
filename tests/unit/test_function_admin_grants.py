"""Unit tests: admin FunctionClient enforces grants on all HTTP methods."""

from __future__ import annotations

import pytest

from snackbase_fn.client import FunctionClient


def test_admin_request_denied_with_empty_grants() -> None:
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=[],
        is_admin=True,
    )
    with pytest.raises(PermissionError, match="no grants"):
        client.get("/api/v1/records/todos")


def test_admin_post_records_requires_write_grant() -> None:
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=["records.read:todos"],
        is_admin=True,
    )
    with pytest.raises(PermissionError, match="grant missing"):
        client.post("/api/v1/records/todos", json={"x": 1})


def test_admin_get_allowed_with_read_grant() -> None:
    """Grant check passes before network; missing host will fail at transport.

    We only assert PermissionError is NOT raised for path grant.
    """
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=["records.read:todos"],
        is_admin=True,
    )
    # Grant gate should allow; network may fail
    try:
        client.get("/api/v1/records/todos")
    except PermissionError:
        pytest.fail("records.read:todos should allow GET")
    except Exception:
        # Network/SSRF/DNS failure is fine — grant was accepted
        pass


def test_admin_wildcard_write_grant() -> None:
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=["records.write:*"],
        is_admin=True,
    )
    try:
        client.post("/api/v1/records/orders", json={})
    except PermissionError:
        pytest.fail("records.write:* should allow POST to any collection")
    except Exception:
        pass


def test_caller_client_skips_grants() -> None:
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=[],
        is_admin=False,
    )
    try:
        client.get("/api/v1/records/todos")
    except PermissionError:
        pytest.fail("non-admin client must not enforce grants")
    except Exception:
        pass


def test_generic_path_denied_without_http_star() -> None:
    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=["records.read:todos"],
        is_admin=True,
    )
    with pytest.raises(PermissionError, match="grant missing"):
        client.get("/api/v1/admin/jobs")
