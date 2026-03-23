from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from app.core.config import settings
from app.db import (
    check_database_connection,
    close_database_engine,
    close_redis,
    get_redis,
    init_redis,
)
from app.routers.redirect import router as redirect_router
from app.routers.urls import router as urls_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await check_database_connection()
    await init_redis()
    yield
    await close_redis()
    await close_database_engine()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(urls_router)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, object]:
    services: dict[str, str] = {}

    try:
        await check_database_connection()
        services["database"] = "ok"
    except Exception as error:
        services["database"] = "error"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "services": services},
        ) from error

    try:
        await get_redis().ping()
        services["redis"] = "ok"
    except Exception as error:
        services["redis"] = "error"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "services": services},
        ) from error

    return {"status": "ok", "services": services}


app.include_router(redirect_router)


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )


if __name__ == "__main__":
    main()
