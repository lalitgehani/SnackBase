"""Dual-client HTTP helpers for function handlers."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from snackbase_fn.egress import SafeTransport

_RECORDS_PATH = re.compile(
    r"^/api/v1/records/(?P<collection>[^/]+)(?P<rest>/.*)?$"
)
_FUNCTION_INVOKE_PATH = re.compile(r"(?:^|/)api/v1/f/")


def nested_function_headers() -> dict[str, str]:
    """Headers for outbound nested function invokes (depth + root).

    Reads FN_DEPTH / FN_ROOT injected by the platform runner and returns
    X-Function-Depth = current+1 so recursive self-invokes consume budget.
    """
    try:
        depth = int(os.environ.get("FN_DEPTH") or "0")
    except ValueError:
        depth = 0
    root = os.environ.get("FN_ROOT") or ""
    headers = {"X-Function-Depth": str(depth + 1)}
    if root:
        headers["X-Function-Root"] = root
    return headers


def is_function_invoke_url(url_or_path: str) -> bool:
    """Return True if the URL/path targets /api/v1/f/ invoke endpoints."""
    if "://" in url_or_path:
        path = urlparse(url_or_path).path or "/"
    else:
        path = url_or_path.split("?", 1)[0]
    return bool(_FUNCTION_INVOKE_PATH.search(path))


class FunctionClient:
    """HTTP client bound to SnackBase API with a specific token."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        grants: list[str] | None = None,
        is_admin: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._grants = grants or []
        self._is_admin = is_admin
        self._used = False
        headers: dict[str, str] = {"accept": "application/json"}
        if token:
            headers["authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=headers,
            transport=SafeTransport(allowed_hosts=self._allowed_hosts(base_url)),
            timeout=30.0,
        )

    @staticmethod
    def _allowed_hosts(base_url: str) -> set[str]:
        host = urlparse(base_url).hostname
        return {host} if host else set()

    def _mark_used(self) -> None:
        self._used = True
        if self._is_admin:
            os.environ["FN_USED_ADMIN_CLIENT"] = "1"

    def _grant_allowed(self, capability: str) -> bool:
        if capability in self._grants:
            return True
        parts = capability.split(":")
        if len(parts) == 2:
            action, _collection = parts
            if f"{action}:*" in self._grants:
                return True
        if "*" in self._grants or "http:*" in self._grants:
            return True
        return False

    def _check_grant(self, capability: str) -> None:
        if not self._is_admin:
            return
        if not self._grants:
            raise PermissionError(
                "Admin client has no grants; configure function grants to allow this operation"
            )
        if not self._grant_allowed(capability):
            raise PermissionError(f"Admin client grant missing: {capability}")

    def _enforce_path_grants(self, method: str, path: str) -> None:
        """Deny-by-default grant check for every admin HTTP call."""
        if not self._is_admin:
            return
        if "://" in path:
            parsed = urlparse(path)
            path = parsed.path or "/"
        path = path.split("?", 1)[0]
        if not path.startswith("/"):
            path = "/" + path

        method_u = method.upper()
        # Nested function invokes are not record ops; allow without record grants
        if is_function_invoke_url(path):
            return

        match = _RECORDS_PATH.match(path)
        if match:
            collection = match.group("collection")
            rest = match.group("rest") or ""
            if "/secrets" in rest or rest.endswith("/secrets") or "secrets" in rest.split("/"):
                self._check_grant(f"records.secrets.read:{collection}")
                return
            if method_u == "GET":
                self._check_grant(f"records.read:{collection}")
            elif method_u in {"POST", "PUT", "PATCH"}:
                self._check_grant(f"records.write:{collection}")
            elif method_u == "DELETE":
                self._check_grant(f"records.delete:{collection}")
            else:
                self._check_grant(f"records.read:{collection}")
            return

        if not self._grants:
            raise PermissionError(
                f"Admin client has no grants for {method_u} {path}"
            )
        if "*" in self._grants or "http:*" in self._grants:
            return
        raise PermissionError(
            f"Admin client grant missing for {method_u} {path} "
            f"(need records.* grant or http:*)"
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        self._mark_used()
        self._enforce_path_grants(method, path)
        merged = dict(headers or {})
        if is_function_invoke_url(path):
            for key, value in nested_function_headers().items():
                # Caller may override; only set if not already provided
                merged.setdefault(key, value)
        return self._client.request(method, path, json=json, params=params, headers=merged)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def records_list(self, collection: str, **params: Any) -> httpx.Response:
        return self.get(f"/api/v1/records/{collection}", params=params)

    def records_create(self, collection: str, data: dict[str, Any]) -> httpx.Response:
        return self.post(f"/api/v1/records/{collection}", json=data)

    def records_update(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> httpx.Response:
        return self.request("PATCH", f"/api/v1/records/{collection}/{record_id}", json=data)

    def records_delete(self, collection: str, record_id: str) -> httpx.Response:
        return self.request("DELETE", f"/api/v1/records/{collection}/{record_id}")

    def close(self) -> None:
        self._client.close()


def get_client() -> FunctionClient:
    """Return a caller-scoped client (respects collection rules)."""
    base_url = os.environ.get("SNACKBASE_URL", "http://127.0.0.1:8090")
    token = os.environ.get("SNACKBASE_CALLER_TOKEN") or os.environ.get("SNACKBASE_ANON_TOKEN")
    return FunctionClient(base_url=base_url, token=token, is_admin=False)


def get_admin_client() -> FunctionClient:
    """Return an admin/service client gated by function grants.

    Requires SNACKBASE_ADMIN_TOKEN to be injected by the runner and
    function grants to authorize record operations.
    """
    base_url = os.environ.get("SNACKBASE_URL", "http://127.0.0.1:8090")
    token = os.environ.get("SNACKBASE_ADMIN_TOKEN")
    if not token:
        raise RuntimeError(
            "Admin client is not available for this invocation "
            "(missing SNACKBASE_ADMIN_TOKEN)"
        )
    grants_raw = os.environ.get("SNACKBASE_FUNCTION_GRANTS", "")
    grants = [g.strip() for g in grants_raw.split(",") if g.strip()]
    return FunctionClient(base_url=base_url, token=token, grants=grants, is_admin=True)
