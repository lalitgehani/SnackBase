"""Unit tests: nested function depth headers from FN_DEPTH/FN_ROOT."""

from __future__ import annotations

import pytest

from snackbase_fn.client import (
    FunctionClient,
    is_function_invoke_url,
    nested_function_headers,
)


def test_nested_headers_increment_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FN_DEPTH", "2")
    monkeypatch.setenv("FN_ROOT", "acct:slug")
    headers = nested_function_headers()
    assert headers["X-Function-Depth"] == "3"
    assert headers["X-Function-Root"] == "acct:slug"


def test_nested_headers_default_depth_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FN_DEPTH", raising=False)
    monkeypatch.delenv("FN_ROOT", raising=False)
    headers = nested_function_headers()
    assert headers["X-Function-Depth"] == "1"
    assert "X-Function-Root" not in headers


def test_is_function_invoke_url() -> None:
    assert is_function_invoke_url("/api/v1/f/acc/hello")
    assert is_function_invoke_url("http://localhost:8090/api/v1/f/acc/hello")
    assert not is_function_invoke_url("/api/v1/records/todos")


def test_client_attaches_depth_on_function_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FN_DEPTH", "0")
    monkeypatch.setenv("FN_ROOT", "fn-sec:recur")

    captured: dict = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {}

    class FakeInner:
        def request(self, method, path, json=None, params=None, headers=None):
            captured["method"] = method
            captured["path"] = path
            captured["headers"] = headers or {}
            return FakeResponse()

    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=[],
        is_admin=False,
    )
    client._client = FakeInner()  # type: ignore[assignment]
    client.request("POST", "/api/v1/f/fn-sec/recur", json={"x": 1})
    assert captured["headers"]["X-Function-Depth"] == "1"
    assert captured["headers"]["X-Function-Root"] == "fn-sec:recur"


def test_client_does_not_attach_depth_on_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FN_DEPTH", "5")
    captured: dict = {}

    class FakeInner:
        def request(self, method, path, json=None, params=None, headers=None):
            captured["headers"] = headers or {}
            return type("R", (), {"status_code": 200})()

    client = FunctionClient(
        base_url="http://example.com",
        token="t",
        grants=["records.read:todos"],
        is_admin=True,
    )
    client._client = FakeInner()  # type: ignore[assignment]
    client.request("GET", "/api/v1/records/todos")
    assert "X-Function-Depth" not in captured["headers"]
