import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    CLICK_SYNC_THRESHOLD,
    RESERVED_SHORT_CODES,
    URL_CACHE_TTL_SECONDS,
)
from app.database import get_db
from app.exceptions import URLExpiredError, URLNotFoundError
from app.redis_client import get_redis, redis_pop_if_at_least
from app.services import URLService


redirect_router = APIRouter(tags=["redirect"])


def cache_set(url: str, expires_ts: int | None) -> str:
    data = {"url": url, "exp": expires_ts}
    return json.dumps(data)


def cache_get(cache_data: str) -> tuple[str, int | None]:
    data = json.loads(cache_data)
    return data["url"], data.get("exp")


async def sync_clicks_to_db(db: AsyncSession, redis, short_code: str):
    click_key = f"clicks:{short_code}"
    clicks = await redis_pop_if_at_least(redis, click_key, CLICK_SYNC_THRESHOLD)
    if clicks is None:
        return
    await URLService.add_clicks(db, short_code, clicks)


async def register_click(redis, db: AsyncSession, short_code: str):
    await redis.incr(f"clicks:{short_code}")
    await sync_clicks_to_db(db, redis, short_code)


def calculate_ttl(expires_ts: int | None) -> int:
    if expires_ts is None:
        return URL_CACHE_TTL_SECONDS
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = expires_ts - now_ts
    return max(min(ttl, URL_CACHE_TTL_SECONDS), 1)


async def get_url_from_cache_or_db(
    redis, db: AsyncSession, short_code: str, now: datetime
) -> tuple[str | None, int | None, bool]:
    lock_key = f"lock:url:{short_code}"
    cache_key = f"url:{short_code}"

    cached_data = await redis.get(cache_key)
    if cached_data:
        original_url, expires_ts = cache_get(cached_data)

        if expires_ts:
            expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc)
            if expires_at < now:
                await redis.delete(cache_key)
                return None, None, False

        return original_url, expires_ts, True

    lock_acquired = await redis.set(lock_key, "1", nx=True, ex=10)
    if not lock_acquired:
        await asyncio.sleep(0.1)
        cached_data = await redis.get(cache_key)
        if cached_data:
            original_url, expires_ts = cache_get(cached_data)
            if expires_ts:
                expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc)
                if expires_at < now:
                    await redis.delete(cache_key)
                    return None, None, False
            return original_url, expires_ts, True

    url = await URLService.get_url_by_code(db, short_code)

    if not url:
        await redis.delete(lock_key)
        return None, None, False

    if url.expires_at and url.expires_at < now:
        await redis.delete(lock_key)
        return None, None, False

    expires_ts = int(url.expires_at.timestamp()) if url.expires_at else None
    cache_value = cache_set(url.original_url, expires_ts)
    ttl = calculate_ttl(expires_ts)
    await redis.set(cache_key, cache_value, ex=ttl)
    await redis.delete(lock_key)

    return url.original_url, expires_ts, True


@redirect_router.get(
    "/{short_code}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def redirect_to_original(
    short_code: str, request: Request, db: AsyncSession = Depends(get_db)
):
    if (
        short_code in RESERVED_SHORT_CODES
        or request.url.path.startswith("/docs")
        or request.url.path.startswith("/redoc")
    ):
        raise URLNotFoundError(short_code)

    redis = await get_redis()
    now = datetime.now(timezone.utc)

    original_url, _, found = await get_url_from_cache_or_db(redis, db, short_code, now)

    if not found:
        if original_url is None:
            raise URLNotFoundError(short_code)
        raise URLExpiredError(short_code)

    await register_click(redis, db, short_code)

    assert original_url is not None
    return RedirectResponse(
        url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
