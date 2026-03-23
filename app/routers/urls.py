from urllib.parse import urljoin

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_redis, get_session
from app.exceptions import (
    RateLimitExceededError,
    ShortURLGenerationError,
    ShortURLNotFoundError,
)
from app.schemas import ShortenRequest, ShortenResponse, StatsResponse
from app.services import (
    create_short_url,
    enforce_rate_limit,
    get_client_identifier,
    get_short_url_stats,
)

router = APIRouter(tags=["urls"])


@router.post(
    "/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED
)
async def shorten_url(
    payload: ShortenRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> ShortenResponse:
    client_id = get_client_identifier(request)
    try:
        await enforce_rate_limit(redis, client_id)
        short_url = await create_short_url(session, redis, str(payload.url))
    except RateLimitExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
        ) from error
    except ShortURLGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return ShortenResponse(
        short_id=short_url.short_id,
        short_url=urljoin(str(request.base_url), short_url.short_id),
    )


@router.get("/stats/{short_id}", response_model=StatsResponse)
async def get_stats(
    short_id: str,
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    try:
        short_url = await get_short_url_stats(session, short_id)
    except ShortURLNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return StatsResponse.model_validate(short_url)
