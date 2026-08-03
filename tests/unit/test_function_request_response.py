"""Unit tests for snackbase_fn Request/Response helpers."""

from snackbase_fn.request import Request
from snackbase_fn.response import Response


def test_request_from_payload() -> None:
    req = Request.from_payload(
        {
            "method": "post",
            "path": "/hello",
            "headers": {"Authorization": "Bearer x", "X-Test": "1"},
            "query": {"a": "b"},
            "json": {"msg": "hi"},
            "auth": {
                "user_id": "u1",
                "email": "a@b.c",
                "account_id": "acc",
                "role": "admin",
            },
        }
    )
    assert req.method == "POST"
    assert req.path == "/hello"
    assert req.headers["authorization"] == "Bearer x"
    assert req.json == {"msg": "hi"}
    assert req.auth.user_id == "u1"
    assert req.auth.email == "a@b.c"


def test_response_json_envelope() -> None:
    resp = Response.json({"ok": True}, status=201)
    env = resp.to_envelope()
    assert env["http_status"] == 201
    assert env["body"] == {"ok": True}
    assert env["status"] == "success"


def test_response_text() -> None:
    resp = Response.text("hello")
    env = resp.to_envelope()
    assert env["body"] == "hello"
    assert "text/plain" in env["headers"]["content-type"]
