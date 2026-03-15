from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                settings.DATABASE_URL, echo=settings.SQL_ECHO
            )
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.get_engine(), class_=AsyncSession, expire_on_commit=False
            )
        return self._session_factory

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = db_manager.get_session_factory()
    async with factory() as session:
        yield session


async def init_db() -> None:
    async with db_manager.get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_manager() -> DatabaseManager:
    return db_manager
