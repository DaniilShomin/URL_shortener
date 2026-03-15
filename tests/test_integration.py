"""
Integration tests require running PostgreSQL and Redis.
Run with: docker-compose up -d && pytest tests/test_integration.py
"""

import pytest
from httpx import AsyncClient, ASGITransport


TEST_API_KEY = "test-api-key"


@pytest.fixture
async def api_client():
    from app.config import settings

    original_key = settings.ADMIN_API_KEY
    settings.ADMIN_API_KEY = TEST_API_KEY

    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    settings.ADMIN_API_KEY = original_key


@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_create_url_requires_api_key(api_client):
    response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_url_with_api_key(api_client):
    response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_url(api_client):
    create_response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    redirect_response = await api_client.get(
        f"/{short_code}",
        follow_redirects=False,
    )
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_get_url_info_requires_auth(api_client):
    response = await api_client.get("/urls/info/test")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_url(api_client):
    create_response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    short_code = create_response.json()["short_code"]

    delete_response = await api_client.delete(
        f"/urls/{short_code}",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_reserved_alias_rejected(api_client):
    response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com", "custom_alias": "health"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "reserved_alias"


@pytest.mark.asyncio
async def test_invalid_alias_format(api_client):
    response = await api_client.post(
        "/urls/shorten",
        json={"original_url": "https://example.com", "custom_alias": "invalid alias!"},
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_alias"


@pytest.mark.asyncio
async def test_url_not_found(api_client):
    response = await api_client.get(
        "/urls/info/nonexistent",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
