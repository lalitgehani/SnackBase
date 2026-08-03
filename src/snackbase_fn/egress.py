"""SSRF-safe httpx transport for function outbound HTTP."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from urllib.parse import urlparse

import httpx


class EgressDeniedError(PermissionError):
    """Raised when an outbound URL is blocked by the egress policy."""


_BLOCKED_PORTS = {25, 587}


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def classify_url(url: str, *, allowed_hosts: Iterable[str] | None = None) -> str:
    """Classify a URL as 'allow' or raise EgressDeniedError.

    Returns 'allow' when the URL is permitted.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise EgressDeniedError(f"Blocked scheme: {parsed.scheme or '(none)'}")

    hostname = parsed.hostname
    if not hostname:
        raise EgressDeniedError("Missing hostname")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if port in _BLOCKED_PORTS:
        raise EgressDeniedError(f"Blocked destination port: {port}")

    allowed = {h.lower() for h in (allowed_hosts or []) if h}
    if hostname.lower() in allowed:
        return "allow"

    # Block obvious metadata / loopback hostnames without DNS
    lowered = hostname.lower()
    if lowered in {"localhost", "metadata.google.internal"} or lowered.endswith(".local"):
        raise EgressDeniedError(f"Blocked host: {hostname}")

    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise EgressDeniedError(f"DNS resolution failed for {hostname}") from exc

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise EgressDeniedError(f"Blocked private/link-local address for {hostname}")

    return "allow"


class SafeTransport(httpx.HTTPTransport):
    """httpx transport that enforces egress policy before connecting."""

    def __init__(self, *, allowed_hosts: Iterable[str] | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._allowed_hosts = set(allowed_hosts or [])

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        classify_url(str(request.url), allowed_hosts=self._allowed_hosts)
        return super().handle_request(request)
