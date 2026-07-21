from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Callable
from uuid import UUID

from app.models.article import Article


@dataclass(frozen=True, slots=True)
class SearchDocumentData:
    article_id: UUID
    source_id: UUID
    source_name: str
    source_slug: str
    title: str
    body: str
    url: str | None
    language_code: str | None
    published_at: datetime | None
    document_hash: str
    builder_version: int
    indexed_at: datetime


class SearchDocumentBuilder:
    VERSION = 1

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self.clock = clock or (lambda: datetime.now(UTC))

    def build(self, article: Article) -> SearchDocumentData:
        if article.id is None or article.content_hash is None or article.normalized_at is None:
            raise ValueError("article must be persisted and normalized before indexing")
        source = article.feed.source
        values = {
            "source_id": str(source.id),
            "source_name": source.name,
            "source_slug": source.slug,
            "title": article.normalized_title or "",
            "body": article.normalized_text or "",
            "url": article.link,
            "language_code": article.language_code,
            "published_at": self._serialize_datetime(article.published_at),
        }
        return SearchDocumentData(
            article_id=article.id,
            source_id=source.id,
            source_name=source.name,
            source_slug=source.slug,
            title=values["title"],
            body=values["body"],
            url=article.link,
            language_code=article.language_code,
            published_at=article.published_at,
            document_hash=sha256(
                json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            builder_version=self.VERSION,
            indexed_at=self.clock(),
        )

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds")
