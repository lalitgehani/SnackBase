"""HEAD support on the admin SPA routes and the health endpoint.

FastAPI's ``APIRoute`` does not derive ``HEAD`` from ``GET`` the way Starlette's
plain ``Route`` does, so both routes answered ``405`` and uptime monitors that
probe with ``HEAD`` reported a working deployment as down.

The admin SPA is served under ``/_/``; the site root is left free for a mounted
application and redirects to the panel when nothing claims it.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI, Response
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


def test_head_admin_root_returns_200_with_empty_body(spa_client: TestClient) -> None:
    response = spa_client.head("/_/")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.content == b""


def test_head_spa_fallback_path_returns_200(spa_client: TestClient) -> None:
    """An unknown path is React Router's to handle, so it gets index.html."""
    assert spa_client.head("/_/admin/login").status_code == 200


def test_head_asset_matches_get_content_length(spa_client: TestClient) -> None:
    head = spa_client.head("/_/assets/app.js")
    get = spa_client.get("/_/assets/app.js")

    assert head.status_code == 200
    assert head.headers["content-length"] == get.headers["content-length"]
    assert head.content == b""


def test_get_admin_root_serves_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/_/")

    assert response.status_code == 200
    assert response.content == INDEX_HTML


def test_bare_admin_path_without_slash_serves_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/_")

    assert response.status_code == 200
    assert response.content == INDEX_HTML


def test_site_root_redirects_to_admin_panel(spa_client: TestClient) -> None:
    """Nothing is mounted at "/" by default, so it points at the panel."""
    response = spa_client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/_/"


def test_root_no_longer_swallows_unknown_api_paths(spa_client: TestClient) -> None:
    """The SPA is no longer a root catch-all, so API paths 404 on their own."""
    assert spa_client.head("/api/v1/nonexistent").status_code == 404
    assert spa_client.get("/api/v1/nonexistent").status_code == 404


def test_mounted_app_can_own_the_site_root(tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    """A root route registered ahead of the redirect takes precedence."""
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_bytes(INDEX_HTML)
    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    register_frontend(app)
    # An application mounts itself and splices its routes to the front.
    added_from = len(app.router.routes)

    @app.get("/", include_in_schema=False)
    async def app_root() -> Response:
        return Response(content=b"the customer app", media_type="text/html")

    added = app.router.routes[added_from:]
    del app.router.routes[added_from:]
    app.router.routes[:0] = added

    client = TestClient(app)
    assert client.get("/", follow_redirects=False).content == b"the customer app"
    assert client.get("/_/").content == INDEX_HTML


def test_head_health_returns_200_with_empty_body(health_client: TestClient) -> None:
    response = health_client.head("/health")

    assert response.status_code == 200
    assert response.content == b""


def test_get_health_still_returns_the_payload(health_client: TestClient) -> None:
    response = health_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
