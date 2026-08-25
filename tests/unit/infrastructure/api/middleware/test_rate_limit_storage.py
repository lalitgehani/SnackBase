"""Unit tests for the token-bucket storage behind rate limiting.

The burst ceiling is expressed as a multiple of the *per-minute* allowance, so
the capacity an operator gets is proportional to the rate they configured. An
earlier absolute reading made `burst=10` a hard ceiling no matter what the rate
said, which is what turned the limiter into an availability failure.
"""

import pytest

from snackbase.infrastructure.api.middleware.rate_limit_storage import (
    RateLimitStorage,
    compute_capacity,
)


@pytest.fixture
def storage() -> RateLimitStorage:
    return RateLimitStorage()


def test_default_multiplier_allows_a_full_minute_of_requests(storage: RateLimitStorage) -> None:
    """60 requests per minute at multiplier 1.0 means 60 in one burst, then 429."""
    for _ in range(60):
        allowed, _, _ = storage.consume("k", 60, burst_multiplier=1.0)
        assert allowed

    allowed, remaining, _ = storage.consume("k", 60, burst_multiplier=1.0)
    assert allowed is False
    assert remaining == 0


def test_multiplier_scales_capacity(storage: RateLimitStorage) -> None:
    """A multiplier of 2.0 doubles the burst allowance."""
    for _ in range(120):
        allowed, _, _ = storage.consume("k", 60, burst_multiplier=2.0)
        assert allowed

    allowed, _, _ = storage.consume("k", 60, burst_multiplier=2.0)
    assert allowed is False


def test_zero_multiplier_floors_at_one_token(storage: RateLimitStorage) -> None:
    """A multiplier of 0 must not lock every caller out — the floor is one token."""
    allowed, _, _ = storage.consume("k", 60, burst_multiplier=0)
    assert allowed

    allowed, _, _ = storage.consume("k", 60, burst_multiplier=0)
    assert allowed is False


def test_peek_does_not_spend_a_token(storage: RateLimitStorage) -> None:
    """peek gates on the limit without charging for it."""
    storage.consume("k", 2, burst_multiplier=1.0)

    for _ in range(5):
        allowed, wait = storage.peek("k", 2, burst_multiplier=1.0)
        assert allowed
        assert wait == 0.0

    storage.consume("k", 2, burst_multiplier=1.0)
    allowed, wait = storage.peek("k", 2, burst_multiplier=1.0)
    assert allowed is False
    assert wait > 0


def test_forget_restores_the_full_allowance(storage: RateLimitStorage) -> None:
    storage.consume("k", 1, burst_multiplier=1.0)
    assert storage.consume("k", 1, burst_multiplier=1.0)[0] is False

    storage.forget("k")
    assert storage.consume("k", 1, burst_multiplier=1.0)[0] is True


@pytest.mark.parametrize(
    ("rate", "multiplier", "expected"),
    [
        (60, 1.0, 60.0),
        (60, 2.0, 120.0),
        (120, 1.0, 120.0),
        (60, 0, 1.0),
        (60, -5, 1.0),
        (0, 1.0, 1.0),
    ],
)
def test_compute_capacity(rate: float, multiplier: float, expected: float) -> None:
    assert compute_capacity(rate, multiplier) == expected
