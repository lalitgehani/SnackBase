"""Unit tests for PermissionCache service."""

import time

import pytest

from snackbase.domain.services import PermissionCache, PermissionResult


class TestPermissionCache:
    """Test suite for PermissionCache."""

    def test_cache_initialization(self):
        """Test cache initializes with correct TTL."""
        cache = PermissionCache(ttl_seconds=300)
        assert cache.ttl_seconds == 300
        assert cache.size() == 0

    def test_cache_set_and_get(self):
        """Test storing and retrieving from cache."""
        cache = PermissionCache(ttl_seconds=300)
        result = PermissionResult(allowed=True, fields=["name", "email"])
        
        cache.set("user123", "customers", "read", result)
        
        retrieved = cache.get("user123", "customers", "read")
        assert retrieved is not None
        assert retrieved.allowed is True
        assert retrieved.fields == ["name", "email"]

    def test_cache_miss(self):
        """Test cache returns None for non-existent keys."""
        cache = PermissionCache(ttl_seconds=300)
        
        result = cache.get("user123", "customers", "read")
        assert result is None

    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        cache = PermissionCache(ttl_seconds=1)  # 1 second TTL
        result = PermissionResult(allowed=True, fields="*")
        
        cache.set("user123", "customers", "read", result)
        
        # Should be available immediately
        assert cache.get("user123", "customers", "read") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("user123", "customers", "read") is None

    def test_invalidate_user(self):
        """Test invalidating all cache entries for a user."""
        cache = PermissionCache(ttl_seconds=300)
        
        # Add multiple entries for same user
        cache.set("user123", "customers", "read", PermissionResult(allowed=True))
        cache.set("user123", "customers", "create", PermissionResult(allowed=False))
        cache.set("user123", "orders", "read", PermissionResult(allowed=True))
        cache.set("user456", "customers", "read", PermissionResult(allowed=True))
        
        assert cache.size() == 4
        
        # Invalidate user123
        cache.invalidate_user("user123")
        
        # user123 entries should be gone
        assert cache.get("user123", "customers", "read") is None
        assert cache.get("user123", "customers", "create") is None
        assert cache.get("user123", "orders", "read") is None
        
        # user456 entry should still exist
        assert cache.get("user456", "customers", "read") is not None
        assert cache.size() == 1

    def test_invalidate_collection(self):
        """Test invalidating all cache entries for a collection."""
        cache = PermissionCache(ttl_seconds=300)
        
        # Add multiple entries for same collection
        cache.set("user123", "customers", "read", PermissionResult(allowed=True))
        cache.set("user123", "customers", "create", PermissionResult(allowed=False))
        cache.set("user456", "customers", "read", PermissionResult(allowed=True))
        cache.set("user123", "orders", "read", PermissionResult(allowed=True))
        
        assert cache.size() == 4
        
        # Invalidate customers collection
        cache.invalidate_collection("customers")
        
        # customers entries should be gone
        assert cache.get("user123", "customers", "read") is None
        assert cache.get("user123", "customers", "create") is None
        assert cache.get("user456", "customers", "read") is None
        
        # orders entry should still exist
        assert cache.get("user123", "orders", "read") is not None
        assert cache.size() == 1

    def test_invalidate_all(self):
        """Test clearing entire cache."""
        cache = PermissionCache(ttl_seconds=300)
        
        cache.set("user123", "customers", "read", PermissionResult(allowed=True))
        cache.set("user456", "orders", "create", PermissionResult(allowed=False))
        
        assert cache.size() == 2
        
        cache.invalidate_all()
        
        assert cache.size() == 0
        assert cache.get("user123", "customers", "read") is None
        assert cache.get("user456", "orders", "create") is None

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = PermissionCache(ttl_seconds=1)
        
        # Add entries
        cache.set("user123", "customers", "read", PermissionResult(allowed=True))
        cache.set("user456", "orders", "create", PermissionResult(allowed=False))
        
        assert cache.size() == 2
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup expired
        removed = cache.cleanup_expired()
        
        assert removed == 2
        assert cache.size() == 0

    def test_cache_key_uniqueness(self):
        """Test that cache keys are unique per user/collection/operation."""
        cache = PermissionCache(ttl_seconds=300)
        
        # Different operations on same collection
        cache.set("user123", "customers", "read", PermissionResult(allowed=True, fields="*"))
        cache.set("user123", "customers", "create", PermissionResult(allowed=False, fields=[]))
        
        read_result = cache.get("user123", "customers", "read")
        create_result = cache.get("user123", "customers", "create")
        
        assert read_result.allowed is True
        assert create_result.allowed is False
        assert cache.size() == 2
