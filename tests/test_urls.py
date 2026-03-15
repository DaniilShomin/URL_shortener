import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_API_KEY = "test-api-key"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


class MockRedis:
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ex=None):
        self._data[key] = value

    async def incr(self, key):
        self._data[key] = str(int(self._data.get(key, 0)) + 1)
        return int(self._data[key])

    async def delete(self, key):
        if key in self._data:
            del self._data[key]

    async def aclose(self):
        pass


mock_redis = MockRedis()


class MockDatabaseManager:
    def __init__(self):
        self._engine = test_engine
        self._session_factory = TestSession

    def get_engine(self):
        return self._engine

    def get_session_factory(self):
        return self._session_factory


class MockRedisManager:
    def __init__(self):
        self._client = mock_redis

    def get_client(self):
        return self._client


@pytest.fixture
async def client():
    import app.database as db_module
    import app.redis_client as redis_module
    import app.config as config_module

    mock_redis._data.clear()

    original_db_manager = db_module.db_manager
    db_module.db_manager = MockDatabaseManager()

    original_redis_manager = redis_module.redis_manager
    redis_module.redis_manager = MockRedisManager()

    original_settings = config_module.settings
    config_module.settings.ADMIN_API_KEY = TEST_API_KEY

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    db_module.db_manager = original_db_manager
    redis_module.redis_manager = original_redis_manager
    config_module.settings = original_settings


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_shorten_url(client):
    response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "example.com" in data["original_url"]


@pytest.mark.asyncio
async def test_redirect(client):
    create_response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 307


@pytest.mark.asyncio
async def test_get_url_info(client):
    create_response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    info_response = await client.get(
        f"/urls/info/{short_code}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert info_response.status_code == 200
    data = info_response.json()
    assert data["short_url"].endswith(short_code)
    assert "example.com" in data["original_url"]


@pytest.mark.asyncio
async def test_click_count_accumulates(client):
    create_response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    for _ in range(3):
        redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
        assert redirect_response.status_code == 307

    info_response = await client.get(
        f"/urls/info/{short_code}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert info_response.status_code == 200
    assert info_response.json()["click_count"] == 3


@pytest.mark.asyncio
async def test_click_count_sync_threshold(client):
    create_response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    for _ in range(12):
        redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
        assert redirect_response.status_code == 307

    info_response = await client.get(
        f"/urls/info/{short_code}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert info_response.status_code == 200
    assert info_response.json()["click_count"] == 12


@pytest.mark.asyncio
async def test_custom_alias(client):
    response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com", "custom_alias": "mycustom"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    assert response.json()["short_code"] == "mycustom"


@pytest.mark.asyncio
async def test_reserved_alias_rejected(client):
    response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com", "custom_alias": "health"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_alias(client):
    await client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com", "custom_alias": "duplicate"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    response = await client.post(
        "/urls/shorten",
        json={"original_url": "https://example2.com", "custom_alias": "duplicate"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 400
