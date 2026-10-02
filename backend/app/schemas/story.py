from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.provider import EntityType


class StorySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    story_id: UUID
    title: str | None
    language_code: str | None
    language_codes: list[str]
    article_count: int = Field(ge=1)
    source_count: int = Field(ge=1)
    first_article_at: datetime
    last_article_at: datetime


class StorySourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: UUID
    name: str
    slug: str
    article_count: int = Field(ge=1)


class StoryArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    membership_id: UUID
    article_id: UUID
    title: str | None
    url: str | None
    published_at: datetime | None
    article_time: datetime
    language_code: str | None
    source_id: UUID
    source_name: str
    source_slug: str
    match_kind: Literal["created", "matched", "retained"]
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_details: dict[str, object] | None
    clustered_at: datetime


class StoryEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: UUID
    canonical_name: str
    entity_type: EntityType
    article_count: int = Field(ge=1)


class StoryTopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: UUID
    name: str
    slug: str
    article_count: int = Field(ge=1)


class StoryDetailRead(StorySummaryRead):
    sources: list[StorySourceRead]
    articles: list[StoryArticleRead]
    entities: list[StoryEntityRead]
    topics: list[StoryTopicRead]


class StoryPageRead(BaseModel):
    items: list[StorySummaryRead]
    total: int
    page: int
    page_size: int
    pages: int
