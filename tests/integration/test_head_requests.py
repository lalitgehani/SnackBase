"""HEAD support on the SPA catch-all and the health endpoint.

FastAPI's ``APIRoute`` does not derive ``HEAD`` from ``GET`` the way Starlette's
plain ``Route`` does, so both routes answered ``405`` and uptime monitors that
probe with ``HEAD`` reported a working deployment as down.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snackbase.infrastructure.api.app import register_frontend, register_health_check

INDEX_HTML = b"<!doctype html><html><body>SnackBase</body></html>"
ASSET_JS = b"console.log('snackbase');\n"


@pytest.fixture
def spa_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """An app serving a minimal built SPA out of ./static."""
    static_dir = tmp_path / "static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_bytes(INDEX_HTML)
    (static_dir / "assets" / "app.js").write_bytes(ASSET_JS)

    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    register_frontend(app)
    return TestClient(app)


@pytest.fixture
def health_client() -> TestClient:
    app = FastAPI()
    register_health_check(app)
    return TestClient(app)


def test_head_root_returns_200_with_empty_body(spa_client: TestClient) -> None:
    response = spa_client.head("/")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.content == b""


def test_head_spa_fallback_path_returns_200(spa_client: TestClient) -> None:
    """An unknown path is React Router's to handle, so it gets index.html."""
    assert spa_client.head("/admin/login").status_code == 200


def test_head_asset_matches_get_content_length(spa_client: TestClient) -> None:
    head = spa_client.head("/assets/app.js")
    get = spa_client.get("/assets/app.js")

    assert head.status_code == 200
    assert head.headers["content-length"] == get.headers["content-length"]
    assert head.content == b""


def test_get_root_still_serves_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/")

    assert response.status_code == 200
    assert response.content == INDEX_HTML


def test_head_unknown_api_path_returns_404_not_the_spa(spa_client: TestClient) -> None:
    """The API guard in the catch-all must hold for HEAD as well as GET."""
    assert spa_client.head("/api/v1/nonexistent").status_code == 404


def test_head_health_returns_200_with_empty_body(health_client: TestClient) -> None:
    response = health_client.head("/health")

    assert response.status_code == 200
    assert response.content == b""


def test_get_health_still_returns_the_payload(health_client: TestClient) -> None:
    response = health_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
