"""Client-IP derivation for rate limiting.

Keying a rate limit on the socket peer is wrong behind a reverse proxy: every
client collapses onto the proxy's address, which turns a per-client limit into
either a shared quota or a denial of service against everyone behind it. Trusting
a forwarding header unconditionally is worse — any client could then forge its own
identity and get an unlimited number of buckets.

Forwarding headers are therefore honoured only when the immediate peer is a
configured trusted proxy (``SNACKBASE_TRUSTED_PROXIES``), which defaults to
loopback — the same convention as ``uvicorn --forwarded-allow-ips``. Entries may
be bare addresses, CIDR networks, or the literal ``*``, so a managed platform
whose edge address is neither stable nor published can still be expressed.

Header precedence, once the peer is trusted:

1. ``CF-Connecting-IP`` — Cloudflare's single unambiguous client address.
2. ``X-Forwarded-For`` — rightmost entry, the one our own proxy appended.
3. The socket peer.

A peer that is *not* trusted but sends a forwarding header is a misconfiguration
worth saying out loud, so it is logged once per distinct peer. The return value is
unchanged in that case: silently believing a header because the request looks
proxied would reintroduce the forgery vector this module exists to close.
"""

import ipaddress

from fastapi import Request

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger

logger = get_logger(__name__)

UNKNOWN_CLIENT = "unknown"

_FORWARDING_HEADERS = ("CF-Connecting-IP", "X-Forwarded-For")

# Peers already warned about, so the hot path does not reprint the same line on
# every request. Bounded because the set is keyed on an attacker-influenced value.
_WARNED_PEERS: set[str] = set()
_WARNED_PEERS_LIMIT = 1024


def _warn_untrusted_proxy(peer: str, request: Request) -> None:
    """Log the shared-bucket misconfiguration once per distinct peer."""
    if not any(header in request.headers for header in _FORWARDING_HEADERS):
        return
    if peer in _WARNED_PEERS:
        return

    if len(_WARNED_PEERS) >= _WARNED_PEERS_LIMIT:
        _WARNED_PEERS.clear()
    _WARNED_PEERS.add(peer)

    logger.warning(
        "Proxied request from an untrusted peer — every client behind this proxy "
        "shares one rate-limit bucket and one login-failure budget. Add the peer to "
        "SNACKBASE_TRUSTED_PROXIES, which accepts bare addresses, CIDR ranges, and "
        "'*' for a platform whose edge address is not stable.",
        peer=peer,
        trusted_proxies=get_settings().trusted_proxies,
    )


def _parse(value: str | None) -> str | None:
    """Return the value if it parses as an IP address, otherwise None."""
    if not value:
        return None
    candidate = value.strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def get_client_ip(request: Request) -> str:
    """Return the address to attribute this request to.

    Args:
        request: The incoming request.

    Returns:
        The forwarded client address when the peer is a trusted proxy, otherwise
        the socket peer address.
    """
    peer = request.client.host if request.client else None
    if peer is None:
        return UNKNOWN_CLIENT

    if not get_settings().trusted_proxy_matcher.matches(peer):
        _warn_untrusted_proxy(peer, request)
        return peer

    cloudflare = _parse(request.headers.get("CF-Connecting-IP"))
    if cloudflare:
        return cloudflare

    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return peer

    # The right-most entry is the one our trusted proxy appended; everything to
    # its left was supplied by upstream hops we cannot vouch for.
    client = forwarded.split(",")[-1].strip()
    return client or peer
