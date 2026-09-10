"""In-process transport for embedding SnackBase in another FastAPI app.

This is a **transport swap, not an authorization bypass**. Every call is
dispatched through the mounted FastAPI application via ``httpx.ASGITransport``,
so routing, authentication, ``check_collection_permission``, and audit logging
execute exactly as they do over the network. The caller's bearer token is sent
on every request. There is no service-role or superadmin bypass path.

Select this client when the backend is embedded in-process. Select the HTTP
client when ``SNACKAPP_BACKEND_URL`` (or ``backend_url``) points at a remote
SnackBase. ``create_client`` is the single factory for that choice.
"""

from __future__ import annotations

import asyncio
import builtins
import os
from collections.abc import Awaitable
from typing import Any, cast

import httpx
from fastapi import FastAPI

IN_PROCESS_USER_AGENT = "SnackBase-InProcess/1.0"
IN_PROCESS_TRANSPORT_HEADER = "in-process"


class SnackBaseClientError(RuntimeError):
    """Raised when a SnackBase API call returns an error status."""

    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"SnackBase {status_code}: {payload}")


def _run_sync(coro: Awaitable[Any]) -> Any:
    """Run ``coro`` from synchronous page functions (threadpool-safe)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already inside an event loop: hop to a fresh loop in a worker thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class _BaseClient:
    """Shared request helpers for in-process and HTTP transports."""

    PAGE_MAX = 100

    def __init__(self, http: httpx.AsyncClient, token: str | None, account: str | None) -> None:
        self._http = http
        self.token = token
        self.account = account

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.account:
            headers["X-Account-ID"] = self.account
        return headers

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._http.request(method, path, headers=self._headers(), **kwargs)
        if response.status_code >= 400:
            try:
                payload: Any = response.json()
            except Exception:
                payload = response.text
            raise SnackBaseClientError(response.status_code, payload)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    @staticmethod
    def _items(payload: Any) -> builtins.list[dict[str, Any]]:
        if isinstance(payload, dict):
            items = payload.get("items") or payload.get("data") or []
            return list(items)
        return list(payload or [])

    async def list(self, collection: str, **params: Any) -> dict[str, Any]:
        want = params.pop("limit", 30) or 30
        skip = params.pop("skip", 0) or 0
        base = {key: value for key, value in params.items() if value is not None}
        out: list[dict[str, Any]] = []
        total = 0
        while len(out) < want:
            page = min(self.PAGE_MAX, want - len(out))
            payload = await self.request(
                "GET",
                f"/api/v1/records/{collection}",
                params={**base, "limit": page, "skip": skip + len(out)},
            )
            items = self._items(payload)
            if isinstance(payload, dict):
                total = payload.get("total", total)
            out.extend(items)
            if len(items) < page:
                break
        return {"items": out, "total": total or len(out)}

    async def get(self, collection: str, record_id: str, expand: str | None = None) -> dict[str, Any]:
        params = {"expand": expand} if expand else None
        return cast(
            dict[str, Any],
            await self.request("GET", f"/api/v1/records/{collection}/{record_id}", params=params),
        )

    async def create(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self.request("POST", f"/api/v1/records/{collection}", json=data),
        )

    async def update(self, collection: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self.request("PATCH", f"/api/v1/records/{collection}/{record_id}", json=data),
        )

    async def delete(self, collection: str, record_id: str) -> None:
        await self.request("DELETE", f"/api/v1/records/{collection}/{record_id}")

    async def aggregate(self, collection: str, **params: Any) -> dict[str, Any]:
        clean = {key: value for key, value in params.items() if value is not None}
        return cast(
            dict[str, Any],
            await self.request("GET", f"/api/v1/records/{collection}/aggregate", params=clean),
        )

    async def me(self) -> dict[str, Any]:
        data = await self.request("GET", "/api/v1/auth/me")
        if isinstance(data, dict):
            data.setdefault("id", data.get("user_id"))
            return cast(dict[str, Any], data)
        return {}

    async def collections(self) -> builtins.list[dict[str, Any]]:
        payload = await self.request("GET", "/api/v1/collections", params={"limit": 200})
        return self._items(payload)

    async def set_rules(self, name: str, rules: dict[str, Any]) -> Any:
        return await self.request("PUT", f"/api/v1/collections/{name}/rules", json=rules)


class InProcessClient(_BaseClient):
    """Async SnackBase client that never opens a TCP connection to itself."""

    def __init__(
        self,
        app: FastAPI,
        token: str | None = None,
        account: str | None = None,
    ) -> None:
        http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://snackbase.local",
            timeout=30.0,
            headers={
                "User-Agent": IN_PROCESS_USER_AGENT,
                "X-SnackBase-Transport": IN_PROCESS_TRANSPORT_HEADER,
            },
        )
        super().__init__(http, token, account)
        self.app = app

    def sync(self) -> SyncInProcessClient:
        """Synchronous facade for page functions running in a threadpool."""
        return SyncInProcessClient(self)

    async def aclose(self) -> None:
        await self._http.aclose()


class HttpClient(_BaseClient):
    """HTTP SnackBase client for a remote ``SNACKAPP_BACKEND_URL``."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        account: str | None = None,
    ) -> None:
        http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=30.0)
        super().__init__(http, token, account)
        self.base_url = base_url.rstrip("/")

    def sync(self) -> SyncHttpClient:
        return SyncHttpClient(self)

    async def aclose(self) -> None:
        await self._http.aclose()


class SyncInProcessClient:
    """Blocking wrapper around :class:`InProcessClient`."""

    def __init__(self, client: InProcessClient) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if callable(attr):

            def _call(*args: Any, **kwargs: Any) -> Any:
                result = attr(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return _run_sync(result)
                return result

            return _call
        return attr


class SyncHttpClient:
    """Blocking wrapper around :class:`HttpClient`."""

    def __init__(self, client: HttpClient) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if callable(attr):

            def _call(*args: Any, **kwargs: Any) -> Any:
                result = attr(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return _run_sync(result)
                return result

            return _call
        return attr


def create_client(
    *,
    app: FastAPI | None = None,
    backend_url: str | None = None,
    token: str | None = None,
    account: str | None = None,
) -> InProcessClient | HttpClient:
    """Return the in-process client when embedded, otherwise the HTTP client.

    ``backend_url`` (or ``SNACKAPP_BACKEND_URL``) selects the HTTP client.
    There is no superadmin or service-role parameter.
    """
    url = backend_url or os.environ.get("SNACKAPP_BACKEND_URL")
    if url:
        return HttpClient(url, token=token, account=account)
    if app is None:
        from snackbase.infrastructure.api.app import app as default_app

        app = default_app
    return InProcessClient(app, token=token, account=account)
