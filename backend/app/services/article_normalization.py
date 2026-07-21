from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.content.normalizer import ContentNormalizer
from app.models.article import Article
from app.repositories.article import ArticleRepository


@dataclass(frozen=True, slots=True)
class ArticleNormalizationBatchResult:
    processed: int
    changed: int
    unchanged: int


class ArticleNormalizationService:
    def __init__(
        self,
        repository: ArticleRepository | None = None,
        normalizer: ContentNormalizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or ArticleRepository()
        self.normalizer = normalizer or ContentNormalizer()
        self.clock = clock or (lambda: datetime.now(UTC))

    def normalize_article(self, article: Article) -> bool:
        result = self.normalizer.normalize(
            title=article.title,
            summary=article.summary,
            content=article.content,
        )
        values = {
            "normalized_title": result.title,
            "normalized_text": result.text,
            "language_code": result.language_code,
            "word_count": result.word_count,
            "reading_time_minutes": result.reading_time_minutes,
            "content_hash": result.content_hash,
            "normalization_version": self.normalizer.VERSION,
        }
        changed = any(getattr(article, key) != value for key, value in values.items())
        for key, value in values.items():
            setattr(article, key, value)
        article.normalized_at = self.clock()
        return changed


class ArticleNormalizationRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: ArticleNormalizationService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.service = service or ArticleNormalizationService()

    def run_pending(self, *, limit: int) -> ArticleNormalizationBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        with self.session_factory() as db:
            with db.begin():
                articles = self.service.repository.list_pending_normalization(
                    db,
                    normalization_version=self.service.normalizer.VERSION,
                    limit=limit,
                )
                changed = sum(self.service.normalize_article(article) for article in articles)
            return ArticleNormalizationBatchResult(
                processed=len(articles),
                changed=changed,
                unchanged=len(articles) - changed,
            )
