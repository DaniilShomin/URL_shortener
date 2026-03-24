import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.exceptions import ShortURLNotFoundError
from app.models import Base, ShortURL
from app.services import (
    create_short_url,
    get_rate_limit_key,
    get_short_url_cache_key,
    get_short_url_stats,
    resolve_short_url,
)


class FakeCache:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def set(self, key: str, value: str, _: int) -> None:
        self.storage[key] = value


class FakeRateLimiter:
    def __init__(self) -> None:
        self.storage: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        current_value = self.storage.get(key, 0) + 1
        self.storage[key] = current_value
        self.expirations.setdefault(key, window_seconds)
        return current_value, self.expirations[key]


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def cache() -> FakeCache:
    return FakeCache()


@pytest.fixture
def rate_limiter() -> FakeRateLimiter:
    return FakeRateLimiter()


@pytest.mark.asyncio
async def test_create_short_url_persists_and_caches(session: AsyncSession, cache: FakeCache):
    short_url = await create_short_url(session, cache, "https://example.com/very/long/path")

    assert short_url.short_id
    assert short_url.original_url == "https://example.com/very/long/path"
    assert (
        cache.storage[get_short_url_cache_key(short_url.short_id)] == short_url.original_url
    )


@pytest.mark.asyncio
async def test_resolve_short_url_increments_click_count(session: AsyncSession, cache: FakeCache):
    created = await create_short_url(session, cache, "https://example.com")

    resolved = await resolve_short_url(session, cache, created.short_id)

    assert resolved == "https://example.com"
    stats = await get_short_url_stats(session, created.short_id)
    assert stats.click_count == 1


@pytest.mark.asyncio
async def test_get_short_url_stats_raises_for_missing_short_id(
    session: AsyncSession,
) -> None:
    with pytest.raises(ShortURLNotFoundError):
        await get_short_url_stats(session, "missing")


@pytest.mark.asyncio
async def test_create_short_url_retries_after_unique_constraint_collision(
    session: AsyncSession,
    cache: FakeCache,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = ShortURL(short_id="duplicate", original_url="https://existing.example")
    session.add(existing)
    await session.commit()

    generated_ids = iter(["duplicate", "unique123"])
    monkeypatch.setattr(
        "app.services.generate_short_id",
        lambda length=None: next(generated_ids),
    )

    created = await create_short_url(session, cache, "https://new.example")

    assert created.short_id == "unique123"
    records = (await session.scalars(select(ShortURL).order_by(ShortURL.id))).all()
    assert [record.short_id for record in records] == ["duplicate", "unique123"]


def test_reserved_short_ids_include_health() -> None:
    from app.routers.redirect import RESERVED_SHORT_IDS

    assert "health" in RESERVED_SHORT_IDS


@pytest.mark.asyncio
async def test_resolve_short_url_uses_cache_key_prefix(session: AsyncSession, cache: FakeCache):
    created = await create_short_url(session, cache, "https://cached.example")
    cache_key = get_short_url_cache_key(created.short_id)

    resolved = await resolve_short_url(session, cache, created.short_id)

    assert resolved == "https://cached.example"
    assert cache_key in cache.storage


@pytest.mark.asyncio
async def test_rate_limit_key_gets_ttl_when_missing(rate_limiter: FakeRateLimiter) -> None:
    from app.services import enforce_rate_limit

    client_id = "127.0.0.1"
    await enforce_rate_limit(rate_limiter, client_id)

    assert rate_limiter.expirations[get_rate_limit_key(client_id)] > 0
