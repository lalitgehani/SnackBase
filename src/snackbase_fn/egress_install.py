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

    try:
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
    except Exception:
        pass

    _INSTALLED = True
