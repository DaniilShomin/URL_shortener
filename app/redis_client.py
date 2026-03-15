import redis.asyncio as redis

from app.config import settings


_GETDEL_LUA = (
    "local v = redis.call('GET', KEYS[1]); "
    "if v then redis.call('DEL', KEYS[1]); end; "
    "return v"
)
_POP_IF_GTE_LUA = (
    "local v = redis.call('GET', KEYS[1]); "
    "if not v then return nil end; "
    "if tonumber(v) < tonumber(ARGV[1]) then return nil end; "
    "redis.call('DEL', KEYS[1]); "
    "return v"
)


class RedisManager:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


redis_manager = RedisManager()


async def get_redis() -> redis.Redis:
    return redis_manager.get_client()


async def redis_getdel(client: redis.Redis, key: str) -> str | None:
    getdel = getattr(client, "getdel", None)
    if callable(getdel):
        return await getdel(key)
    return await client.eval(_GETDEL_LUA, 1, key)


async def redis_pop_if_at_least(
    client: redis.Redis, key: str, minimum: int
) -> int | None:
    if minimum <= 0:
        value = await redis_getdel(client, key)
        return int(value) if value is not None else None

    eval_fn = getattr(client, "eval", None)
    if callable(eval_fn):
        value = await eval_fn(_POP_IF_GTE_LUA, 1, key, str(minimum))
        return int(value) if value is not None else None

    value = await client.get(key)
    if value is None:
        return None
    clicks = int(value)
    if clicks < minimum:
        return None
    await client.delete(key)
    return clicks


async def close_redis() -> None:
    await redis_manager.close()
