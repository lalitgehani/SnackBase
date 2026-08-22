"""JWKS client for trusted-issuer (platform) token verification.

Constructs lazily on first use when platform auth is enabled. Importing this
module performs no network I/O.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

import httpx
import jwt
from jwt import PyJWKSet

from snackbase.core.config import Settings, get_settings
from snackbase.infrastructure.auth.token_codec import AuthenticationError

MAX_CACHED_KEYS = 16
MIN_REFETCH_INTERVAL_SECONDS = 10


class PlatformJWKSClient:
    """Fetch and cache signing keys from the configured platform JWKS endpoint."""

    def __init__(self, settings: Settings) -> None:
        if not settings.platform_jwks_url:
            raise ValueError("platform_jwks_url is required for PlatformJWKSClient")
        self._jwks_url = settings.platform_jwks_url
        self._cache_seconds = settings.platform_jwks_cache_seconds
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._last_refetch_at: float = 0.0
        self._lock = Lock()

    def get_signing_key(self, token: str) -> Any:
        """Return the public key for the token's ``kid``, refreshing the cache as needed."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid token") from exc

        kid = header.get("kid")
        if not kid:
            raise AuthenticationError("Token missing key id (kid)")

        cache_was_valid = self._cache_is_valid()
        if not cache_was_valid:
            self._fetch_keys(rate_limited=False)

        key = self._keys.get(kid)
        if key is not None:
            return key

        # Key rotation: refetch once when the cache was already warm but lacks this kid.
        if cache_was_valid:
            self._fetch_keys(rate_limited=True)

        key = self._keys.get(kid)
        if key is None:
            raise AuthenticationError("Unknown signing key")
        return key

    def _cache_is_valid(self) -> bool:
        with self._lock:
            if not self._keys:
                return False
            return (time.monotonic() - self._fetched_at) <= self._cache_seconds

    def _fetch_keys(self, *, rate_limited: bool) -> None:
        with self._lock:
            now = time.monotonic()
            if rate_limited and (now - self._last_refetch_at) < MIN_REFETCH_INTERVAL_SECONDS:
                return

            try:
                response = httpx.get(self._jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks_data = response.json()
            except (httpx.HTTPError, OSError, ValueError) as exc:
                raise AuthenticationError("Failed to fetch signing keys") from exc

            if not isinstance(jwks_data, dict) or not isinstance(jwks_data.get("keys"), list):
                raise AuthenticationError("Invalid JWKS response")

            keys_list = jwks_data["keys"][:MAX_CACHED_KEYS]
            try:
                jwks = PyJWKSet.from_dict({"keys": keys_list})
            except Exception as exc:
                raise AuthenticationError("Invalid JWKS response") from exc

            self._keys = {
                jwk.key_id: jwk.key for jwk in jwks.keys if jwk.key_id is not None
            }
            self._fetched_at = now
            self._last_refetch_at = now


_client: PlatformJWKSClient | None = None
_client_lock = Lock()


def get_platform_jwks_client() -> PlatformJWKSClient | None:
    """Return the shared JWKS client, or None when platform auth is disabled."""
    settings = get_settings()
    if not settings.platform_auth_enabled:
        return None

    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = PlatformJWKSClient(settings)
    return _client


def reset_platform_jwks_client() -> None:
    """Reset the lazy singleton (for tests)."""
    global _client
    with _client_lock:
        _client = None
