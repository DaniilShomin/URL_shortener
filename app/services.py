import secrets
import string

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions import (
    RateLimitExceededError,
    ShortURLGenerationError,
    ShortURLNotFoundError,
)
from app.models import ShortURL
from app.storage import CacheBackend, RateLimiterBackend

settings = get_settings()
ALPHABET = string.ascii_letters + string.digits
REDIS_PREFIX = "shortener"


def get_short_url_cache_key(short_id: str) -> str:
    return f"{REDIS_PREFIX}:short_url:{short_id}"


def get_rate_limit_key(client_id: str) -> str:
    return f"{REDIS_PREFIX}:rate_limit:shorten:{client_id}"


def generate_short_id(length: int | None = None) -> str:
    size = length or settings.short_id_length
    return "".join(secrets.choice(ALPHABET) for _ in range(size))


def get_client_identifier(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


async def enforce_rate_limit(rate_limiter: RateLimiterBackend, client_id: str) -> None:
    key = get_rate_limit_key(client_id)
    current_count, _ = await rate_limiter.increment(
        key,
        settings.rate_limit_window_seconds,
    )

    if current_count > settings.rate_limit_requests:
        raise RateLimitExceededError("Rate limit exceeded")


async def create_short_url(
    session: AsyncSession,
    cache: CacheBackend,
    original_url: str,
) -> ShortURL:
    for _ in range(10):
        short_id = generate_short_id()
        short_url = ShortURL(short_id=short_id, original_url=original_url)
        session.add(short_url)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue

        await session.refresh(short_url)
        try:
            await cache_original_url(cache, short_id, original_url)
        except Exception:
            pass
        return short_url

    raise ShortURLGenerationError("Unable to generate unique short id")


async def cache_original_url(cache: CacheBackend, short_id: str, original_url: str) -> None:
    await cache.set(
        get_short_url_cache_key(short_id),
        original_url,
        settings.redirect_cache_ttl_seconds,
    )


async def resolve_short_url(
    session: AsyncSession,
    cache: CacheBackend,
    short_id: str,
) -> str:
    cached_url = await cache.get(get_short_url_cache_key(short_id))

    if cached_url is not None:
        increment_result = await session.execute(
            update(ShortURL)
            .where(ShortURL.short_id == short_id)
            .values(click_count=ShortURL.click_count + 1)
            .returning(ShortURL.short_id)
        )
        if increment_result.scalar_one_or_none() is None:
            await session.rollback()
            raise ShortURLNotFoundError("Short URL not found")

        await session.commit()
        return cached_url

    resolved_row = await session.execute(
        update(ShortURL)
        .where(ShortURL.short_id == short_id)
        .values(click_count=ShortURL.click_count + 1)
        .returning(ShortURL.original_url)
    )
    original_url = resolved_row.scalar_one_or_none()
    if original_url is None:
        await session.rollback()
        raise ShortURLNotFoundError("Short URL not found")

    await session.commit()
    try:
        await cache_original_url(cache, short_id, original_url)
    except Exception:
        pass
    return original_url


async def get_short_url_stats(session: AsyncSession, short_id: str) -> ShortURL:
    short_url = await session.scalar(select(ShortURL).where(ShortURL.short_id == short_id))
    if short_url is None:
        raise ShortURLNotFoundError("Short URL not found")
    return short_url
