from fastapi import HTTPException, Header, status
from app.config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if not settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return True


async def optional_api_key(x_api_key: str | None = Header(None)):
    if not settings.ADMIN_API_KEY:
        return True
    if x_api_key is None:
        return False
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return True
