from datetime import datetime, timezone
from typing import Optional

import shortuuid
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import RESERVED_SHORT_CODES
from app.exceptions import (
    AliasAlreadyExistsError,
    InvalidAliasError,
    ReservedAliasError,
    URLNotFoundError,
)
from app.models import URL


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
        return dt.replace(tzinfo=None)
    return dt


class URLService:
    @staticmethod
    def generate_short_code() -> str:
        return shortuuid.ShortUUID().random(length=settings.SHORT_CODE_LENGTH)

    @staticmethod
    def validate_alias(alias: str | None) -> str | None:
        if alias is None:
            return None
        if alias in RESERVED_SHORT_CODES:
            raise ReservedAliasError(alias)
        if len(alias) > settings.MAX_CUSTOM_ALIAS_LENGTH:
            raise InvalidAliasError(
                f"Alias too long. Max {settings.MAX_CUSTOM_ALIAS_LENGTH} characters."
            )
        if not alias.replace("-", "").replace("_", "").isalnum():
            raise InvalidAliasError(
                "Alias can only contain letters, numbers, hyphens and underscores."
            )
        return alias

    @staticmethod
    async def create_url(
        db: AsyncSession,
        original_url: str,
        custom_alias: str | None = None,
        expires_at: Optional[datetime] = None,
    ) -> URL:
        custom_alias = URLService.validate_alias(custom_alias)
        short_code = custom_alias if custom_alias else URLService.generate_short_code()

        expires_at_utc = _to_naive_utc(expires_at)

        url = URL(
            short_code=short_code, original_url=original_url, expires_at=expires_at_utc
        )
        db.add(url)
        try:
            await db.commit()
            await db.refresh(url)
            return url
        except IntegrityError:
            await db.rollback()
            raise AliasAlreadyExistsError(custom_alias or short_code)

    @staticmethod
    async def get_url_by_code(db: AsyncSession, short_code: str) -> URL | None:
        result = await db.execute(select(URL).where(URL.short_code == short_code))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_url_or_raise(db: AsyncSession, short_code: str) -> URL:
        url = await URLService.get_url_by_code(db, short_code)
        if url is None:
            raise URLNotFoundError(short_code)
        return url

    @staticmethod
    async def increment_click_count(db: AsyncSession, url: URL) -> None:
        url.click_count += 1
        await db.commit()

    @staticmethod
    async def add_clicks(db: AsyncSession, short_code: str, delta: int) -> None:
        if delta <= 0:
            return
        await db.execute(
            update(URL)
            .where(URL.short_code == short_code)
            .values(click_count=URL.click_count + delta)
        )
        await db.commit()

    @staticmethod
    async def delete_url(db: AsyncSession, short_code: str) -> bool:
        url = await URLService.get_url_by_code(db, short_code)
        if url:
            await db.delete(url)
            await db.commit()
            return True
        return False
