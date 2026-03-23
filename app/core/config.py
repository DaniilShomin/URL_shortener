from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "URL Shortener"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/url_shortener"
    )
    redis_url: str = "redis://localhost:6379/0"
    short_id_length: int = 8
    redirect_cache_ttl_seconds: int = 3600
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
