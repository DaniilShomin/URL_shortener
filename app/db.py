from collections.abc import AsyncGenerator
from inspect import isawaitable

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client: Redis | None = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


async def init_redis() -> None:
    global redis_client

    if redis_client is None:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            ping_result = client.ping()
            if isawaitable(ping_result):
                await ping_result
        except Exception:
            await client.aclose()
            raise

        redis_client = client


async def close_redis() -> None:
    global redis_client

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database_engine() -> None:
    await engine.dispose()
