from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: HttpUrl

    active: bool = True
    priority: int = Field(default=3, ge=1, le=4)
    fetch_interval_minutes: int = Field(default=30, gt=0)


class FeedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: HttpUrl | None = None

    active: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    fetch_interval_minutes: int | None = Field(default=None, gt=0)


class FeedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID

    name: str
    url: str

    active: bool
    priority: int
    fetch_interval_minutes: int

    last_fetched_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None

    etag: str | None
    last_modified: str | None

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
