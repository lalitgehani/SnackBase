"""Unit tests for function egress / SSRF classification."""

import pytest

from snackbase_fn.egress import EgressDeniedError, classify_url


def test_block_loopback() -> None:
    with pytest.raises(EgressDeniedError):
        classify_url("http://127.0.0.1/")


def test_block_localhost() -> None:
    with pytest.raises(EgressDeniedError):
        classify_url("http://localhost:8080/")


def test_block_metadata() -> None:
    with pytest.raises(EgressDeniedError):
        classify_url("http://169.254.169.254/latest/meta-data/")


def test_block_smtp_ports() -> None:
    with pytest.raises(EgressDeniedError, match="port"):
        classify_url("https://example.com:25/")


def test_allow_configured_host_even_if_loopback_name() -> None:
    # Allowed hosts bypass IP checks for SNACKBASE_URL destinations
    assert classify_url("http://127.0.0.1:8090/api", allowed_hosts=["127.0.0.1"]) == "allow"


def test_allow_public_https() -> None:
    assert classify_url("https://example.com/") == "allow"
