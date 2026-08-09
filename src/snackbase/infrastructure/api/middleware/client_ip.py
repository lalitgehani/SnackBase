"""Client-IP derivation for rate limiting.

Keying a rate limit on the socket peer is wrong behind a reverse proxy: every
client collapses onto the proxy's address, which turns a per-client limit into
either a shared quota or a denial of service against everyone behind it. Trusting
``X-Forwarded-For`` unconditionally is worse — any client could then forge its own
identity and get an unlimited number of buckets.

The header is therefore honoured only when the immediate peer is a configured
trusted proxy, which defaults to loopback (the same convention as
``uvicorn --forwarded-allow-ips``).
"""

from fastapi import Request

from snackbase.core.config import get_settings

UNKNOWN_CLIENT = "unknown"


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

    if peer not in set(get_settings().trusted_proxies):
        return peer

    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return peer

    # The right-most entry is the one our trusted proxy appended; everything to
    # its left was supplied by upstream hops we cannot vouch for.
    client = forwarded.split(",")[-1].strip()
    return client or peer
