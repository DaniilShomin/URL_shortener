from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.db import get_cache_backend, get_session
from app.exceptions import ShortURLNotFoundError
from app.services import resolve_short_url
from app.storage import CacheBackend

router = APIRouter(tags=["redirect"])
RESERVED_SHORT_IDS = {"health", "shorten", "stats", "docs", "openapi.json", "redoc"}


@router.get("/{short_id}", include_in_schema=False)
async def redirect_to_url(
    short_id: str,
    session: AsyncSession = Depends(get_session),
    cache: CacheBackend = Depends(get_cache_backend),
) -> RedirectResponse:
    if short_id in RESERVED_SHORT_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )
    try:
        original_url = await resolve_short_url(session, cache, short_id)
    except ShortURLNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return RedirectResponse(original_url, status_code=307)
