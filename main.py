from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.database import db_manager, init_db
from app.exceptions import register_exception_handlers
from app.middleware import LoggingMiddleware, RequestIDMiddleware
from app.redis_client import close_redis, redis_manager
from app.routers import urls
from app.routers import redirect
from app.config import settings
from app.rate_limit import limiter
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    await init_db()
    yield
    await close_redis()
    await db_manager.close()
    logger.info("Application shutting down")


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )


app = FastAPI(
    title="URL Shortener API",
    description="Bitly-like URL shortener service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.state.limiter = limiter
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=len(settings.get_cors_origins()) > 0
    and "*" not in settings.get_cors_origins(),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/ready")
async def readiness_check():
    checks = {"database": "down", "redis": "down"}

    try:
        engine = db_manager.get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception:
        pass

    try:
        r = redis_manager.get_client()
        await r.ping()
        checks["redis"] = "up"
    except Exception:
        pass

    all_up = all(v == "up" for v in checks.values())
    status_code = 200 if all_up else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_up else "not_ready", "checks": checks},
    )


app.include_router(urls.router)
app.include_router(redirect.redirect_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
