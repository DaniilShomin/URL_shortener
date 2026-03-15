from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/url_shortener"
    )
    SQL_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    BASE_URL: str = "http://localhost:8000"
    SHORT_CODE_LENGTH: int = 8
    MAX_CUSTOM_ALIAS_LENGTH: int = 50
    ADMIN_API_KEY: str = ""
    CORS_ORIGINS: Union[List[str], str] = []

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str) and self.CORS_ORIGINS.startswith("["):
            try:
                return json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                return []
        return [self.CORS_ORIGINS] if self.CORS_ORIGINS else []


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
