"""Unit tests for platform JWKS client (F2.2)."""

import time
from unittest.mock import MagicMock, patch

import pytest
from jwt import PyJWKSet
from tests.helpers.platform_tokens import build_jwks, generate_rsa_keypair, mint_platform_token

from snackbase.core.config import Settings
from snackbase.infrastructure.auth.platform_jwks import (
    MAX_CACHED_KEYS,
    PlatformJWKSClient,
    get_platform_jwks_client,
    reset_platform_jwks_client,
)
from snackbase.infrastructure.auth.token_codec import AuthenticationError


@pytest.fixture(autouse=True)
def _reset_client():
    reset_platform_jwks_client()
    yield
    reset_platform_jwks_client()


def _settings(**overrides: object) -> Settings:
    base = {
        "platform_issuer": "https://platform.example.com",
        "platform_jwks_url": "http://localhost:9999/jwks",
        "platform_audience": "snackbase-instance",
        "platform_jwks_cache_seconds": 300,
        "single_tenant_mode": True,
        "single_tenant_account": "app",
    }
    base.update(overrides)
    return Settings(**base)


def test_import_with_no_issuer_performs_no_network_call():
    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get") as mock_get:
        client = get_platform_jwks_client()
        assert client is None
        mock_get.assert_not_called()


def test_cache_hit_within_ttl_issues_one_fetch():
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key)
    jwks = build_jwks(public_key)
    client = PlatformJWKSClient(_settings())

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = jwks

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response) as mock_get:
        client.get_signing_key(token)
        client.get_signing_key(token)
        assert mock_get.call_count == 1


def test_unknown_kid_triggers_refetch_and_succeeds_on_rotation():
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key, kid="rotated-key")
    rotated_jwks = build_jwks(public_key, kid="rotated-key")
    client = PlatformJWKSClient(_settings(platform_jwks_cache_seconds=300))

    # Simulate a warm cache from a previous key rotation generation.
    old_jwks = PyJWKSet.from_dict(build_jwks(public_key, kid="old-key"))
    client._keys = {jwk.key_id: jwk.key for jwk in old_jwks.keys if jwk.key_id}
    client._fetched_at = time.monotonic()

    rotated_response = MagicMock()
    rotated_response.raise_for_status = MagicMock()
    rotated_response.json.return_value = rotated_jwks

    with patch(
        "snackbase.infrastructure.auth.platform_jwks.httpx.get",
        return_value=rotated_response,
    ) as mock_get:
        key = client.get_signing_key(token)
        assert key is not None
        assert mock_get.call_count == 1


def test_unknown_kid_after_refetch_raises_authentication_error():
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key, kid="missing-key")
    jwks = build_jwks(public_key, kid="other-key")
    client = PlatformJWKSClient(_settings())

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = jwks

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response):
        with pytest.raises(AuthenticationError, match="Unknown signing key"):
            client.get_signing_key(token)


def test_refetch_rate_limit_two_unknown_kids_one_fetch():
    private_key, public_key = generate_rsa_keypair()
    token_one = mint_platform_token(private_key, kid="kid-a")
    token_two = mint_platform_token(private_key, kid="kid-b")
    jwks = build_jwks(public_key, kid="present-key")
    client = PlatformJWKSClient(_settings())

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = jwks

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response) as mock_get:
        with pytest.raises(AuthenticationError):
            client.get_signing_key(token_one)
        with pytest.raises(AuthenticationError):
            client.get_signing_key(token_two)
        assert mock_get.call_count == 1


def test_transport_error_raises_authentication_error():
    private_key, _ = generate_rsa_keypair()
    token = mint_platform_token(private_key)
    client = PlatformJWKSClient(_settings())

    with patch(
        "snackbase.infrastructure.auth.platform_jwks.httpx.get",
        side_effect=OSError("connection refused"),
    ):
        with pytest.raises(AuthenticationError, match="Failed to fetch signing keys"):
            client.get_signing_key(token)


def test_malformed_jwks_raises_authentication_error():
    private_key, _ = generate_rsa_keypair()
    token = mint_platform_token(private_key)
    client = PlatformJWKSClient(_settings())

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"not_keys": []}

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response):
        with pytest.raises(AuthenticationError, match="Invalid JWKS response"):
            client.get_signing_key(token)


def test_jwks_truncated_to_sixteen_keys():
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key)
    single = build_jwks(public_key)["keys"][0]
    oversized = {"keys": [{**single, "kid": f"k{i}"} for i in range(100)]}
    client = PlatformJWKSClient(_settings())

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = oversized

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response):
        with pytest.raises(AuthenticationError):
            client.get_signing_key(token)

    assert len(client._keys) <= MAX_CACHED_KEYS


def test_cache_expiry_triggers_refetch():
    private_key, public_key = generate_rsa_keypair()
    token = mint_platform_token(private_key)
    jwks = build_jwks(public_key)
    client = PlatformJWKSClient(_settings(platform_jwks_cache_seconds=1))

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = jwks

    with patch("snackbase.infrastructure.auth.platform_jwks.httpx.get", return_value=mock_response) as mock_get:
        client.get_signing_key(token)
        client._fetched_at = 0.0
        client.get_signing_key(token)
        assert mock_get.call_count == 2
