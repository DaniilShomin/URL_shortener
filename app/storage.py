from __future__ import annotations

from inspect import isawaitable
from typing import Protocol

from redis.asyncio import Redis


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...


class RateLimiterBackend(Protocol):
    async def increment(self, key: str, window_seconds: int) -> tuple[int, int | None]: ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...


class RedisCacheBackend:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.client.setex(key, ttl_seconds, value)

    async def ping(self) -> bool:
        result = self.client.ping()
        if isawaitable(result):
            await result
        return True

    async def close(self) -> None:
        await self.client.aclose()


class RedisRateLimiterBackend:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int | None]:
        current_count = await self.client.incr(key)
        ttl = await self.client.ttl(key)
        if ttl is None or ttl < 0:
            await self.client.expire(key, window_seconds)
            ttl = window_seconds
        return current_count, ttl

    async def ping(self) -> bool:
        result = self.client.ping()
        if isawaitable(result):
            await result
        return True

    async def close(self) -> None:
        await self.client.aclose()


class InMemoryCacheBackend:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del ttl_seconds
        self.storage[key] = value

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class InMemoryRateLimiterBackend:
    def __init__(self) -> None:
        self.storage: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int | None]:
        current_count = self.storage.get(key, 0) + 1
        self.storage[key] = current_count
        ttl = self.expirations.get(key)
        if ttl is None or ttl < 0:
            self.expirations[key] = window_seconds
            ttl = window_seconds
        return current_count, ttl

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class NoOpCacheBackend:
    async def get(self, key: str) -> str | None:
        del key
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del key, value, ttl_seconds

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


async def try_create_cache_backend(redis_url: str) -> CacheBackend | None:
    client = Redis.from_url(redis_url, decode_responses=True)
    backend = RedisCacheBackend(client)
    try:
        await backend.ping()
    except Exception:
        await client.aclose()
        return None
    return backend


async def try_create_rate_limiter_backend(redis_url: str) -> RateLimiterBackend | None:
    client = Redis.from_url(redis_url, decode_responses=True)
    backend = RedisRateLimiterBackend(client)
    try:
        await backend.ping()
    except Exception:
        await client.aclose()
        return None
    return backend
