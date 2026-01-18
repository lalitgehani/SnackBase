"""In-memory storage for rate limiting counters.

This module provides a thread-safe in-memory storage for tracking rate limit
tokens using a token bucket (sliding window) algorithm.
"""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict


@dataclass
class TokenBucket:
    """Token bucket for a specific key (IP or User)."""

    tokens: float
    last_updated: float


class RateLimitStorage:
    """Thread-safe in-memory storage for rate limit counters."""

    def __init__(self, cleanup_interval: int = 3600):
        """Initialize storage.

        Args:
            cleanup_interval: Interval in seconds to clean up stale entries.
        """
        self._storage: Dict[str, TokenBucket] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval

    def consume(
        self, key: str, rate_per_minute: float, burst: float = 1.0
    ) -> tuple[bool, int, float]:
        """Attempt to consume a token for the given key.

        Args:
            key: The unique key (IP address or User ID).
            rate_per_minute: Allowed requests per minute.
            burst: Maximum burst capacity (multiplier of rate_per_second).

        Returns:
            A tuple of (is_allowed, remaining_tokens, reset_time).
        """
        now = time.time()
        rate_per_second = rate_per_minute / 60.0
        # Burst is at least 1 token, or a multiplier of the rate
        capacity = max(1.0, burst)

        with self._lock:
            # Periodic cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_stale(now)

            bucket = self._storage.get(key)

            if bucket is None:
                # First request for this key
                # We start with capacity - 1 because we consume one right away
                bucket = TokenBucket(tokens=capacity - 1.0, last_updated=now)
                self._storage[key] = bucket
                
                # Reset time is when we'll have exactly 1 token again
                reset_time = 1.0 / rate_per_second
                return True, int(bucket.tokens), reset_time

            # Refill tokens based on time passed
            elapsed = now - bucket.last_updated
            refill = elapsed * rate_per_second
            bucket.tokens = min(capacity, bucket.tokens + refill)
            bucket.last_updated = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                # Reset time is when we'll have (current_tokens + 1) tokens
                # but if we're full, it might be 0.
                # Standard practice: Reset time is time until next token or time until full?
                # Usually X-RateLimit-Reset is seconds until the limit fully resets to maximum.
                reset_seconds = (capacity - bucket.tokens) / rate_per_second
                return True, int(bucket.tokens), reset_seconds
            else:
                # Rate limit exceeded
                wait_seconds = (1.0 - bucket.tokens) / rate_per_second
                reset_seconds = (capacity - bucket.tokens) / rate_per_second
                return False, 0, wait_seconds

    def _cleanup_stale(self, now: float) -> None:
        """Remove entries that haven't been updated for a while."""
        # Simple policy: remove if not updated in the last hour
        stale_threshold = 3600
        to_delete = [
            k for k, v in self._storage.items() 
            if now - v.last_updated > stale_threshold
        ]
        for k in to_delete:
            del self._storage[k]
        self._last_cleanup = now


# Global instance
rate_limit_storage = RateLimitStorage()
