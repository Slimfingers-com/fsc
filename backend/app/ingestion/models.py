from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FeedFormat(str, Enum):
    RSS = "rss"
    ATOM = "atom"


@dataclass(frozen=True, slots=True)
class FeedFetchRequest:
    url: str
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class FeedFetchResult:
    requested_url: str
    final_url: str
    status_code: int
    content: bytes | None
    content_type: str | None
    etag: str | None
    last_modified: str | None

    @property
    def not_modified(self) -> bool:
        return self.status_code == 304


@dataclass(frozen=True, slots=True)
class ParsedFeedEnclosure:
    url: str
    content_type: str | None
    length_bytes: int | None


@dataclass(frozen=True, slots=True)
class ParsedFeedEntry:
    external_id: str | None
    title: str | None
    link: str | None
    summary: str | None
    content: str | None
    author: str | None
    published_at: datetime | None
    updated_at: datetime | None
    categories: tuple[str, ...]
    enclosures: tuple[ParsedFeedEnclosure, ...]


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    source_url: str
    format: FeedFormat
    version: str
    title: str | None
    link: str | None
    description: str | None
    language: str | None
    updated_at: datetime | None
    entries: tuple[ParsedFeedEntry, ...]
    warnings: tuple[str, ...]
