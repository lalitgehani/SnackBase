"""Install process-wide egress policy for function runtimes.

Called from bootstrap so raw ``httpx`` / ``urllib`` usage is subject to the
same SSRF deny rules as ``FunctionClient``. Also propagates nested function
invoke depth headers on outbound ``/api/v1/f/`` requests.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

_INSTALLED = False


def install_egress_policy(*, allowed_hosts: set[str] | None = None) -> None:
    """Monkey-patch httpx and urllib to enforce egress classification."""
    global _INSTALLED
    if _INSTALLED:
        return

    hosts = set(allowed_hosts or set())
    snackbase_url = os.environ.get("SNACKBASE_URL", "")
    if snackbase_url:
        host = urlparse(snackbase_url).hostname
        if host:
            hosts.add(host)

    import httpx

    from snackbase_fn.client import is_function_invoke_url, nested_function_headers
    from snackbase_fn.egress import SafeTransport, classify_url

    _orig_client_init = httpx.Client.__init__

    def _client_init(self: Any, *args: Any, **kwargs: Any) -> None:
        transport = kwargs.get("transport")
        if transport is None or not isinstance(transport, SafeTransport):
            kwargs["transport"] = SafeTransport(allowed_hosts=hosts)
        _orig_client_init(self, *args, **kwargs)

        # Event hooks: nested depth on function invoke URLs
        hooks = dict(getattr(self, "event_hooks", None) or {})
        req_hooks = list(hooks.get("request") or [])

        def _depth_hook(request: httpx.Request) -> None:
            if is_function_invoke_url(str(request.url)):
                for key, value in nested_function_headers().items():
                    if key not in request.headers:
                        request.headers[key] = value

        req_hooks.insert(0, _depth_hook)
        hooks["request"] = req_hooks
        self.event_hooks = hooks

    httpx.Client.__init__ = _client_init  # type: ignore[method-assign]

    if hasattr(httpx, "AsyncClient"):
        _orig_async_init = httpx.AsyncClient.__init__

        def _async_init(self: Any, *args: Any, **kwargs: Any) -> None:
            _orig_async_init(self, *args, **kwargs)
            self.event_hooks = dict(self.event_hooks or {})
            hooks = list(self.event_hooks.get("request") or [])

            async def _classify_hook(request: httpx.Request) -> None:
                classify_url(str(request.url), allowed_hosts=hosts)
                if is_function_invoke_url(str(request.url)):
                    for key, value in nested_function_headers().items():
                        if key not in request.headers:
                            request.headers[key] = value

            hooks.insert(0, _classify_hook)
            self.event_hooks["request"] = hooks

        httpx.AsyncClient.__init__ = _async_init  # type: ignore[method-assign]

    import urllib.request

    _orig_urlopen = urllib.request.urlopen

    def _safe_urlopen(url: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(url, str):
            url_str = url
        else:
            url_str = getattr(url, "full_url", None) or str(url)
        classify_url(url_str, allowed_hosts=hosts)
        return _orig_urlopen(url, *args, **kwargs)

    urllib.request.urlopen = _safe_urlopen  # type: ignore[assignment]

    _install_socket_policy(hosts)

    _INSTALLED = True


def _install_socket_policy(hosts: set[str]) -> None:
    """Apply the egress policy at the socket layer.

    Patching only httpx and urllib leaves `socket.create_connection` — and any
    library built on it — completely unguarded. Classifying at `connect` covers
    every caller that goes through the socket module, which is the last point
    all of Python's networking shares.

    This is defence in depth, not containment: handler code can still reach the
    syscall through `ctypes`. Only the OS-level sandbox actually bounds egress.
    """
    import socket as _socket

    from snackbase_fn.egress import classify_address

    # By the time a connection reaches `connect`, the hostname has already been
    # resolved, so an allowed host arrives as a bare IP. Resolve the allowlist
    # once here or the SnackBase API itself — routinely on loopback in
    # development — would be denied by its own policy.
    allowed = set(hosts)
    for host in hosts:
        try:
            for info in _socket.getaddrinfo(host, None, type=_socket.SOCK_STREAM):
                allowed.add(str(info[4][0]))
        except OSError:
            continue

    def _check(address: Any) -> None:
        if not isinstance(address, tuple) or len(address) < 2:
            return  # AF_UNIX and friends never leave the host
        host, port = address[0], address[1]
        if not isinstance(host, str) or not isinstance(port, int):
            return
        classify_address(host, port, allowed_hosts=allowed)

    _orig_connect = _socket.socket.connect

    def _safe_connect(self: Any, address: Any) -> Any:
        if self.family in (_socket.AF_INET, _socket.AF_INET6):
            _check(address)
        return _orig_connect(self, address)

    _socket.socket.connect = _safe_connect  # type: ignore[method-assign]

    _orig_connect_ex = _socket.socket.connect_ex

    def _safe_connect_ex(self: Any, address: Any) -> Any:
        if self.family in (_socket.AF_INET, _socket.AF_INET6):
            _check(address)
        return _orig_connect_ex(self, address)

    _socket.socket.connect_ex = _safe_connect_ex  # type: ignore[method-assign]
