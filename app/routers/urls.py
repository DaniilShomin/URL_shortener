from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import verify_api_key
from app.config import settings
from app.database import get_db
from app.exceptions import URLNotFoundError
from app.redis_client import get_redis
from app.routers.redirect import cache_set, calculate_ttl
from app.schemas import URLCreate, URLInfo, URLResponse
from app.services import URLService


limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/urls", tags=["urls"])


@router.post(
    "/shorten", response_model=URLResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def shorten_url(
    request: Request,
    url_data: URLCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
):
    original_url = str(url_data.original_url)

    url = await URLService.create_url(
        db=db,
        original_url=original_url,
        custom_alias=url_data.custom_alias,
        expires_at=url_data.expires_at,
    )

    redis = await get_redis()
    expires_ts = int(url.expires_at.timestamp()) if url.expires_at else None
    cache_value = cache_set(url.original_url, expires_ts)
    ttl = calculate_ttl(expires_ts)
    await redis.set(f"url:{url.short_code}", cache_value, ex=ttl)

    return url


@router.get("/info/{short_code}", response_model=URLInfo)
@limiter.limit("30/minute")
async def get_url_info(
    request: Request,
    short_code: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
):
    redis = await get_redis()
    cached_clicks = await redis.get(f"clicks:{short_code}")

    url = await URLService.get_url_or_raise(db, short_code)

    click_count = url.click_count + (int(cached_clicks) if cached_clicks else 0)

    return URLInfo(
        short_url=f"{settings.BASE_URL}/{short_code}",
        original_url=url.original_url,
        click_count=click_count,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_url(
    request: Request,
    short_code: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
):
    redis = await get_redis()
    await redis.delete(f"url:{short_code}")
    await redis.delete(f"clicks:{short_code}")

    deleted = await URLService.delete_url(db, short_code)

    if not deleted:
        raise URLNotFoundError(short_code)
