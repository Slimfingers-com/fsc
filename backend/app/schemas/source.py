from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.enums.coverage_scope import CoverageScope
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate, FeedRead


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

    url: HttpUrl
    api_url: HttpUrl | None = None

    source_type: SourceType
    coverage_scope: CoverageScope | None = None

    country: str | None = Field(default=None, min_length=2, max_length=2)
    language: str | None = Field(default=None, min_length=2, max_length=10)

    ownership: str | None = None
    funding_model: str | None = Field(default=None, max_length=100)

    paywall: bool = False
    transparency_level: int | None = Field(default=None, ge=0, le=100)
    correction_policy: str | None = None
    primary_source_usage: int | None = Field(default=None, ge=0, le=100)
    priority_tier: int = Field(default=3, ge=1, le=4)

    feeds: list[FeedCreate] = Field(default_factory=list)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    normalized_name: str

    description: str | None

    url: str
    api_url: str | None

    source_type: SourceType
    coverage_scope: CoverageScope | None

    country: str | None
    language: str | None

    ownership: str | None
    funding_model: str | None

    paywall: bool
    active: bool

    transparency_level: int | None
    correction_policy: str | None
    primary_source_usage: int | None
    priority_tier: int

    feeds: list[FeedRead]
