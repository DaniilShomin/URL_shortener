from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Base
from app.storage import (
    CacheBackend,
    InMemoryCacheBackend,
    InMemoryRateLimiterBackend,
    NoOpCacheBackend,
    RateLimiterBackend,
    try_create_cache_backend,
    try_create_rate_limiter_backend,
)

settings = get_settings()

engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
database_mode = "primary"
cache_backend: CacheBackend | None = None
rate_limiter_backend: RateLimiterBackend | None = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def get_database_status() -> str:
    return "degraded" if database_mode == "fallback" else "ok"


async def init_database() -> None:
    global database_mode

    try:
        await check_database_connection()
        database_mode = "primary"
    except Exception:
        if not settings.database_fallback_enabled:
            raise
        await _switch_database(settings.database_fallback_url)
        await _ensure_database_schema()
        await check_database_connection()
        database_mode = "fallback"


def get_cache_backend() -> CacheBackend:
    if cache_backend is None:
        raise RuntimeError("Cache backend is not initialized")
    return cache_backend


def get_rate_limiter_backend() -> RateLimiterBackend:
    if rate_limiter_backend is None:
        raise RuntimeError("Rate limiter backend is not initialized")
    return rate_limiter_backend


async def init_storage() -> None:
    global cache_backend, rate_limiter_backend

    if cache_backend is None:
        cache_backend = await _build_cache_backend()

    if rate_limiter_backend is None:
        rate_limiter_backend = await _build_rate_limiter_backend()


async def close_storage() -> None:
    global cache_backend, rate_limiter_backend

    current_cache_backend = cache_backend
    current_rate_limiter_backend = rate_limiter_backend

    if current_cache_backend is not None:
        await current_cache_backend.close()
        cache_backend = None

    if current_rate_limiter_backend is not None:
        if current_rate_limiter_backend is not current_cache_backend:
            await current_rate_limiter_backend.close()
        rate_limiter_backend = None


async def check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database_engine() -> None:
    await engine.dispose()


async def _build_cache_backend() -> CacheBackend:
    backend_name = settings.cache_backend.lower()
    if backend_name == "memory":
        return InMemoryCacheBackend()
    if backend_name == "noop":
        return NoOpCacheBackend()
    if backend_name == "redis":
        backend = await try_create_cache_backend(settings.redis_url)
        if backend is not None:
            return backend
        return InMemoryCacheBackend()
    raise ValueError(f"Unsupported cache backend: {settings.cache_backend}")


async def _build_rate_limiter_backend() -> RateLimiterBackend:
    backend_name = settings.rate_limiter_backend.lower()
    if backend_name == "memory":
        return InMemoryRateLimiterBackend()
    if backend_name == "redis":
        backend = await try_create_rate_limiter_backend(settings.redis_url)
        if backend is not None:
            return backend
        return InMemoryRateLimiterBackend()
    raise ValueError(
        f"Unsupported rate limiter backend: {settings.rate_limiter_backend}"
    )


async def _switch_database(database_url: str) -> None:
    global engine, SessionLocal

    await engine.dispose()
    engine = create_async_engine(database_url, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _ensure_database_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
