from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

class SearchSort(StrEnum):
    RELEVANCE = "relevance"
    NEWEST = "newest"
    OLDEST = "oldest"


@dataclass(frozen=True, slots=True)
class SearchFilters:
    language_code: str | None = None
    source_id: UUID | None = None
    source_slug: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: UUID
    article_id: UUID
    title: str
    excerpt: str
    url: str | None
    source_id: UUID
    source_name: str
    source_slug: str
    language_code: str | None
    published_at: datetime | None
    relevance: float


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: list[SearchHit]
    total: int
    page: int
    page_size: int


class SearchProvider(ABC):
    @abstractmethod
    def search(
        self, *,
        query: str | None,
        filters: SearchFilters,
        sort: SearchSort,
        page: int,
        page_size: int,
    ) -> SearchPage: ...
