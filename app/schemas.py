from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]


class URLInfo(BaseModel):
    short_url: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]
