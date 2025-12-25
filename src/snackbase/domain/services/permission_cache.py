"""Permission cache service with TTL support.

Provides in-memory caching of resolved permissions with configurable TTL.
Thread-safe implementation for concurrent access.
"""

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Cache entry with TTL support.
    
    Attributes:
        value: The cached value.
        expires_at: Unix timestamp when this entry expires.
    """
    
    value: Any
    expires_at: float


class PermissionCache:
    """Thread-safe TTL-based cache for resolved permissions.
    
    Cache keys are formatted as: {user_id}:{collection}:{operation}
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """Initialize the cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 5 minutes).
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
    
    def _make_key(self, user_id: str, collection: str, operation: str) -> str:
        """Create cache key from components.
        
        Args:
            user_id: User ID.
            collection: Collection name.
            operation: Operation type (create, read, update, delete).
            
        Returns:
            Cache key string.
        """
        return f"{user_id}:{collection}:{operation}"
    
    def get(self, user_id: str, collection: str, operation: str) -> Any | None:
        """Get cached permission result.
        
        Args:
            user_id: User ID.
            collection: Collection name.
            operation: Operation type.
            
        Returns:
            Cached value if found and not expired, None otherwise.
        """
        key = self._make_key(user_id, collection, operation)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                # Remove expired entry
                del self._cache[key]
                return None
            
            return entry.value
    
    def set(self, user_id: str, collection: str, operation: str, value: Any) -> None:
        """Store permission result in cache.
        
        Args:
            user_id: User ID.
            collection: Collection name.
            operation: Operation type.
            value: Value to cache.
        """
        key = self._make_key(user_id, collection, operation)
        expires_at = time.time() + self.ttl_seconds
        
        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
    
    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cache entries for a user.
        
        Args:
            user_id: User ID to invalidate.
        """
        with self._lock:
            # Find all keys for this user
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"{user_id}:")
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
    
    def invalidate_collection(self, collection: str) -> None:
        """Invalidate all cache entries for a collection.
        
        Args:
            collection: Collection name to invalidate.
        """
        with self._lock:
            # Find all keys for this collection
            keys_to_delete = [
                key for key in self._cache.keys()
                if f":{collection}:" in key
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
    
    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.
        
        Returns:
            Number of entries removed.
        """
        with self._lock:
            current_time = time.time()
            keys_to_delete = [
                key for key, entry in self._cache.items()
                if current_time > entry.expires_at
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            return len(keys_to_delete)
    
    
    def get_user_groups(self, user_id: str) -> list[str] | None:
        """Get cached groups for a user.
        
        Args:
            user_id: User ID.
            
        Returns:
            List of group names if found and not expired, None otherwise.
        """
        key = f"{user_id}:__groups__"
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if time.time() > entry.expires_at:
                del self._cache[key]
                return None
            
            return entry.value

    def set_user_groups(self, user_id: str, groups: list[str]) -> None:
        """Cache groups for a user.
        
        Args:
            user_id: User ID.
            groups: List of group names.
        """
        key = f"{user_id}:__groups__"
        expires_at = time.time() + self.ttl_seconds
        
        with self._lock:
            self._cache[key] = CacheEntry(value=groups, expires_at=expires_at)

    def size(self) -> int:
        """Get current cache size.
        
        Returns:
            Number of entries in cache.
        """
        with self._lock:
            return len(self._cache)
