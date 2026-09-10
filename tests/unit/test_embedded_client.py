"""Unit tests for the in-process / HTTP client factory."""

import inspect

from snackbase.embedded import HttpClient, InProcessClient, create_client


def test_factory_returns_inprocess_when_embedded():
    from fastapi import FastAPI

    app = FastAPI()
    client = create_client(app=app, token="tok")
    assert isinstance(client, InProcessClient)
    assert not isinstance(client, HttpClient)
    assert client.token == "tok"


def test_factory_returns_http_when_url_configured():
    client = create_client(backend_url="http://example.invalid:8090", token="tok")
    assert isinstance(client, HttpClient)
    assert client.base_url == "http://example.invalid:8090"


def test_factory_env_url_selects_http(monkeypatch):
    monkeypatch.setenv("SNACKAPP_BACKEND_URL", "http://remote.example:8000")
    client = create_client(token="tok")
    assert isinstance(client, HttpClient)


def test_no_service_role_parameter():
    signature = inspect.signature(create_client)
    assert "service_role" not in signature.parameters
    assert "superadmin" not in signature.parameters
    inprocess_sig = inspect.signature(InProcessClient.__init__)
    assert "service_role" not in inprocess_sig.parameters
    for name in ("list", "get", "create", "update", "delete", "aggregate", "me", "collections", "set_rules"):
        method_sig = inspect.signature(getattr(InProcessClient, name))
        assert "service_role" not in method_sig.parameters
        assert "superadmin" not in method_sig.parameters
