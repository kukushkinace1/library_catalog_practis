import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Any:
        """Get value from cache by key."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Save value to cache with optional TTL."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete cached value by key."""

    @abstractmethod
    async def delete_by_prefix(self, prefix: str) -> None:
        """Delete cached values by key prefix."""

    async def close(self) -> None:
        """Close backend resources if needed."""


class InMemoryCache(CacheBackend):
    """Simple in-memory cache with TTL support."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None

            value, expires_at = item
            if expires_at is not None and expires_at <= time.monotonic():
                self._store.pop(key, None)
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = None if ttl is None else time.monotonic() + ttl
        async with self._lock:
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def delete_by_prefix(self, prefix: str) -> None:
        async with self._lock:
            keys_to_delete = [key for key in self._store if key.startswith(prefix)]
            for key in keys_to_delete:
                self._store.pop(key, None)


class RedisCache(CacheBackend):
    """Redis-backed cache backend."""

    def __init__(self, redis_url: str):
        if Redis is None:
            raise RuntimeError(
                "Redis support requires the 'redis' package to be installed"
            )
        self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Any:
        raw_value = await self._redis.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        payload = json.dumps(value)
        await self._redis.set(key, payload, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def delete_by_prefix(self, prefix: str) -> None:
        cursor = 0
        pattern = f"{prefix}*"
        while True:
            cursor, keys = await self._redis.scan(cursor=cursor, match=pattern)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break

    async def close(self) -> None:
        await self._redis.aclose()


def create_cache_backend(
    backend: str,
    redis_url: str | None = None,
) -> CacheBackend:
    """Create cache backend from settings."""
    if backend == "redis":
        if not redis_url:
            logger.warning("CACHE_BACKEND=redis but REDIS_URL is empty, using in-memory cache")
            return InMemoryCache()
        try:
            return RedisCache(redis_url)
        except RuntimeError as exc:
            logger.warning("%s Falling back to in-memory cache.", exc)
            return InMemoryCache()

    return InMemoryCache()
