from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from app.logger import logger


class URLNotFoundError(Exception):
    pass


class AliasAlreadyExistsError(Exception):
    pass


class ReservedAliasError(Exception):
    pass


class InvalidAliasError(Exception):
    pass


class URLExpiredError(Exception):
    pass


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def url_not_found_handler(
    request: Request, exc: URLNotFoundError
) -> JSONResponse:
    logger.warning(
        "url_not_found",
        extra={"short_code": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "not_found", "detail": str(exc)},
    )


async def alias_already_exists_handler(
    request: Request, exc: AliasAlreadyExistsError
) -> JSONResponse:
    logger.warning(
        "alias_already_exists",
        extra={"alias": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "alias_exists", "detail": str(exc)},
    )


async def reserved_alias_handler(
    request: Request, exc: ReservedAliasError
) -> JSONResponse:
    logger.warning(
        "reserved_alias",
        extra={"alias": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "reserved_alias", "detail": str(exc)},
    )


async def invalid_alias_handler(
    request: Request, exc: InvalidAliasError
) -> JSONResponse:
    logger.warning(
        "invalid_alias",
        extra={"detail": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "invalid_alias", "detail": str(exc)},
    )


async def url_expired_handler(request: Request, exc: URLExpiredError) -> JSONResponse:
    logger.warning(
        "url_expired",
        extra={"short_code": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={"error": "expired", "detail": str(exc)},
    )


async def database_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error(
        "database_error",
        extra={"error": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "detail": "Database error occurred"},
    )


async def redis_error_handler(request: Request, exc: RedisError) -> JSONResponse:
    logger.error(
        "redis_error", extra={"error": str(exc), "request_id": _get_request_id(request)}
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "service_unavailable", "detail": "Cache service unavailable"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={"error": str(exc), "request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "detail": "An unexpected error occurred"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(URLNotFoundError, url_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AliasAlreadyExistsError, alias_already_exists_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ReservedAliasError, reserved_alias_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidAliasError, invalid_alias_handler)  # type: ignore[arg-type]
    app.add_exception_handler(URLExpiredError, url_expired_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, database_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RedisError, redis_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]
