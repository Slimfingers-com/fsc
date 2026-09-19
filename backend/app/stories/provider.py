from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.analysis.provider import EntityType


class StorySort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    LARGEST = "largest"


@dataclass(frozen=True, slots=True)
class StoryFilters:
    language_code: str | None = None
    source_id: UUID | None = None
    source_slug: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    entity_id: UUID | None = None
    entity_type: EntityType | None = None
    topic_id: UUID | None = None
    topic_slug: str | None = None
    min_articles: int = 1
    min_sources: int = 1


@dataclass(frozen=True, slots=True)
class StorySummary:
    story_id: UUID
    title: str | None
    language_code: str | None
    article_count: int
    source_count: int
    first_article_at: datetime
    last_article_at: datetime


@dataclass(frozen=True, slots=True)
class StorySource:
    source_id: UUID
    name: str
    slug: str
    article_count: int


@dataclass(frozen=True, slots=True)
class StoryArticleItem:
    membership_id: UUID
    article_id: UUID
    title: str | None
    url: str | None
    article_time: datetime
    source_id: UUID
    source_name: str
    source_slug: str
    match_kind: str
    similarity_score: float
    match_details: dict[str, object] | None
    clustered_at: datetime


@dataclass(frozen=True, slots=True)
class StoryEntity:
    entity_id: UUID
    canonical_name: str
    entity_type: EntityType
    article_count: int


@dataclass(frozen=True, slots=True)
class StoryTopic:
    topic_id: UUID
    name: str
    slug: str
    article_count: int


@dataclass(frozen=True, slots=True)
class StoryDetail:
    summary: StorySummary
    sources: list[StorySource]
    articles: list[StoryArticleItem]
    entities: list[StoryEntity]
    topics: list[StoryTopic]


@dataclass(frozen=True, slots=True)
class StoryPage:
    items: list[StorySummary]
    total: int
    page: int
    page_size: int
