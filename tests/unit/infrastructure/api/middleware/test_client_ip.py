"""Unit tests for client-IP attribution behind reverse proxies.

The rate limiter and the login-failure budget are both keyed on what this module
returns, so getting it wrong behind a proxy either shares one quota across every
visitor or lets a client mint an unlimited number of buckets.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from starlette.datastructures import Headers

from snackbase.core.config import Settings, parse_trusted_proxies
from snackbase.infrastructure.api.middleware import client_ip as client_ip_module
from snackbase.infrastructure.api.middleware.client_ip import UNKNOWN_CLIENT, get_client_ip


def _request(peer: str | None, **headers: str) -> Any:
    """The smallest thing `get_client_ip` needs: a peer address and headers."""
    return SimpleNamespace(
        client=SimpleNamespace(host=peer) if peer is not None else None,
        headers=Headers(headers),
    )


@pytest.fixture(autouse=True)
def reset_warned_peers():
    client_ip_module._WARNED_PEERS.clear()
    yield
    client_ip_module._WARNED_PEERS.clear()


def _with_proxies(*entries: str):
    return patch.object(
        client_ip_module,
        "get_settings",
        return_value=Settings(trusted_proxies=list(entries)),
    )


# --------------------------------------------------------------------------- #
# F3.1: CIDR ranges and the explicit wildcard
# --------------------------------------------------------------------------- #


def test_peer_inside_a_cidr_has_forwarded_for_honoured():
    with _with_proxies("10.0.0.0/8"):
        request = _request("10.1.2.3", **{"X-Forwarded-For": "203.0.113.10"})
        assert get_client_ip(request) == "203.0.113.10"


def test_peer_outside_a_cidr_has_forwarded_for_ignored():
    with _with_proxies("10.0.0.0/8"):
        request = _request("192.0.2.5", **{"X-Forwarded-For": "203.0.113.10"})
        assert get_client_ip(request) == "192.0.2.5"


def test_wildcard_trusts_any_peer():
    with _with_proxies("*"):
        request = _request("198.51.100.77", **{"X-Forwarded-For": "203.0.113.10"})
        assert get_client_ip(request) == "203.0.113.10"


def test_default_loopback_entries_behave_as_before():
    with _with_proxies("127.0.0.1", "::1"):
        assert get_client_ip(_request("127.0.0.1", **{"X-Forwarded-For": "8.8.8.8"})) == "8.8.8.8"
        assert get_client_ip(_request("::1", **{"X-Forwarded-For": "8.8.8.8"})) == "8.8.8.8"
        forged = _request("203.0.113.77", **{"X-Forwarded-For": "8.8.8.8"})
        assert get_client_ip(forged) == "203.0.113.77"


def test_ipv6_cidr_matches_an_ipv6_peer():
    with _with_proxies("fd00::/8"):
        request = _request("fd00::1234", **{"X-Forwarded-For": "203.0.113.10"})
        assert get_client_ip(request) == "203.0.113.10"


def test_unparseable_entry_raises_naming_the_entry():
    with pytest.raises(ValueError, match="not-an-ip"):
        parse_trusted_proxies(["10.0.0.0/8", "not-an-ip"])

    with pytest.raises(ValueError, match="not-an-ip"):
        Settings(trusted_proxies=["not-an-ip"])


def test_entries_are_parsed_once_not_per_request():
    settings = Settings(trusted_proxies=["10.0.0.0/8"])
    first = settings.trusted_proxy_matcher

    with patch.object(client_ip_module, "get_settings", return_value=settings):
        for _ in range(5):
            get_client_ip(_request("10.0.0.1", **{"X-Forwarded-For": "203.0.113.10"}))

    assert settings.trusted_proxy_matcher is first


def test_missing_peer_returns_unknown():
    with _with_proxies("*"):
        assert get_client_ip(_request(None)) == UNKNOWN_CLIENT


# --------------------------------------------------------------------------- #
# F3.2: CF-Connecting-IP
# --------------------------------------------------------------------------- #


def test_cf_connecting_ip_from_a_trusted_peer_is_returned():
    with _with_proxies("*"):
        request = _request("10.0.0.1", **{"CF-Connecting-IP": "203.0.113.7"})
        assert get_client_ip(request) == "203.0.113.7"


def test_cf_connecting_ip_takes_precedence_over_forwarded_for():
    with _with_proxies("*"):
        request = _request(
            "10.0.0.1",
            **{"CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "203.0.113.10"},
        )
        assert get_client_ip(request) == "203.0.113.7"


def test_cf_connecting_ip_from_an_untrusted_peer_is_ignored():
    with _with_proxies("127.0.0.1"):
        request = _request("203.0.113.77", **{"CF-Connecting-IP": "8.8.8.8"})
        assert get_client_ip(request) == "203.0.113.77"


def test_malformed_cf_connecting_ip_falls_back_to_forwarded_for():
    with _with_proxies("*"):
        request = _request(
            "10.0.0.1",
            **{"CF-Connecting-IP": "not-an-ip", "X-Forwarded-For": "203.0.113.10"},
        )
        assert get_client_ip(request) == "203.0.113.10"


def test_malformed_cf_connecting_ip_without_forwarded_for_falls_back_to_peer():
    with _with_proxies("*"):
        request = _request("10.0.0.1", **{"CF-Connecting-IP": "not-an-ip"})
        assert get_client_ip(request) == "10.0.0.1"


def test_header_lookup_is_case_insensitive():
    with _with_proxies("*"):
        request = _request("10.0.0.1", **{"cf-connecting-ip": "203.0.113.7"})
        assert get_client_ip(request) == "203.0.113.7"


def test_forwarded_for_uses_the_rightmost_entry():
    with _with_proxies("*"):
        request = _request(
            "10.0.0.1", **{"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 203.0.113.10"}
        )
        assert get_client_ip(request) == "203.0.113.10"


# --------------------------------------------------------------------------- #
# F3.3: the proxied-but-untrusted warning
# --------------------------------------------------------------------------- #


def test_untrusted_peer_with_forwarded_for_warns_once():
    with _with_proxies("127.0.0.1"), patch.object(client_ip_module.logger, "warning") as warn:
        for _ in range(11):
            request = _request("203.0.113.77", **{"X-Forwarded-For": "8.8.8.8"})
            assert get_client_ip(request) == "203.0.113.77"

        assert warn.call_count == 1
        message, kwargs = warn.call_args[0][0], warn.call_args[1]
        assert "SNACKBASE_TRUSTED_PROXIES" in message
        assert kwargs["peer"] == "203.0.113.77"


def test_untrusted_peer_with_cf_connecting_ip_warns():
    with _with_proxies("127.0.0.1"), patch.object(client_ip_module.logger, "warning") as warn:
        request = _request("203.0.113.77", **{"CF-Connecting-IP": "8.8.8.8"})
        assert get_client_ip(request) == "203.0.113.77"
        assert warn.call_count == 1


def test_untrusted_peer_without_forwarding_headers_does_not_warn():
    with _with_proxies("127.0.0.1"), patch.object(client_ip_module.logger, "warning") as warn:
        assert get_client_ip(_request("203.0.113.77")) == "203.0.113.77"
        assert warn.call_count == 0


def test_trusted_peer_does_not_warn():
    with _with_proxies("*"), patch.object(client_ip_module.logger, "warning") as warn:
        request = _request("203.0.113.77", **{"X-Forwarded-For": "8.8.8.8"})
        assert get_client_ip(request) == "8.8.8.8"
        assert warn.call_count == 0


def test_warned_peer_set_is_bounded():
    with _with_proxies("127.0.0.1"):
        for octet in range(client_ip_module._WARNED_PEERS_LIMIT + 5):
            request = _request(f"10.{octet // 256}.{octet % 256}.1", **{"X-Forwarded-For": "8.8.8.8"})
            get_client_ip(request)

        assert len(client_ip_module._WARNED_PEERS) <= client_ip_module._WARNED_PEERS_LIMIT
