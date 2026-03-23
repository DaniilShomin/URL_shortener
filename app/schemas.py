from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class ShortenRequest(BaseModel):
    url: AnyHttpUrl


class ShortenResponse(BaseModel):
    short_id: str
    short_url: str


class StatsResponse(BaseModel):
    short_id: str
    click_count: int

    model_config = ConfigDict(from_attributes=True)
