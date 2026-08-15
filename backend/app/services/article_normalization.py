from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.content.normalizer import ContentNormalizer
from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.repositories.article import ArticleRepository
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ArticleNormalizationBatchResult:
    processed: int
    changed: int
    unchanged: int


class ArticleNormalizationService:
    PROVIDER = "content_normalizer"
    CONFIG_VERSION = "1"

    def __init__(
        self,
        repository: ArticleRepository | None = None,
        normalizer: ContentNormalizer | None = None,
        clock: Callable[[], datetime] | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.repository = repository or ArticleRepository()
        self.normalizer = normalizer or ContentNormalizer()
        self.clock = clock or (lambda: datetime.now(UTC))
        self.config_version = config_version

    @property
    def provider_version(self) -> str:
        return str(self.normalizer.VERSION)

    def input_hash(
        self,
        article: Article,
    ) -> str:
        payload = [
            article.title or "",
            article.summary or "",
            article.content or "",
        ]

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def candidate(
        self,
        article: Article,
    ) -> ArticleProcessingCandidate:
        if article.id is None:
            raise ValueError(
                "article must be persisted before normalization"
            )

        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.input_hash(article),
            provider=self.PROVIDER,
            provider_version=self.provider_version,
            configuration_version=self.config_version,
        )

    def normalize_article(
        self,
        article: Article,
    ) -> bool:
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

        changed = any(
            getattr(article, key) != value
            for key, value in values.items()
        )

        for key, value in values.items():
            setattr(article, key, value)

        article.normalized_at = self.clock()

        return changed


class ArticleNormalizationRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: ArticleNormalizationService | None = None,
        processing_repository: ArticleProcessingRepository | None = None,
        *,
        claim_ttl_seconds: float = 300,
        retry_base_seconds: float = 30,
        retry_max_seconds: float = 3600,
        worker_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            claim_ttl_seconds <= 0
            or retry_base_seconds <= 0
            or retry_max_seconds < retry_base_seconds
        ):
            raise ValueError(
                "claim and retry timing settings are invalid"
            )

        self.session_factory = session_factory
        self.service = service or ArticleNormalizationService()
        self.processing_repository = (
            processing_repository
            or ArticleProcessingRepository()
        )

        self.claim_ttl_seconds = claim_ttl_seconds
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds

        self.worker_id = worker_id or str(uuid4())
        self.clock = clock or (
            lambda: datetime.now(UTC)
        )

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[ArticleProcessingClaim]:
        claims: list[ArticleProcessingClaim] = []

        page_size = max(
            100,
            limit * 4,
        )

        last_created_at = None
        last_article_id = None

        while len(claims) < limit:
            conditions = [
                Article.deleted_at.is_(None),
            ]

            if (
                last_created_at is not None
                and last_article_id is not None
            ):
                conditions.append(
                    or_(
                        Article.created_at > last_created_at,
                        and_(
                            Article.created_at == last_created_at,
                            Article.id > last_article_id,
                        ),
                    )
                )

            articles = list(
                db.scalars(
                    select(Article)
                    .where(*conditions)
                    .order_by(
                        Article.created_at,
                        Article.id,
                    )
                    .limit(page_size)
                ).all()
            )

            if not articles:
                break

            candidates = [
                self.service.candidate(article)
                for article in articles
            ]

            claims.extend(
                self.processing_repository.claim_candidates(
                    db,
                    pipeline=ArticlePipeline.NORMALIZATION.value,
                    candidates=candidates,
                    worker_id=self.worker_id,
                    now=now,
                    claim_expires_at=(
                        now
                        + timedelta(
                            seconds=self.claim_ttl_seconds
                        )
                    ),
                    limit=limit - len(claims),
                )
            )

            last_article = articles[-1]
            last_created_at = last_article.created_at
            last_article_id = last_article.id

            if len(articles) < page_size:
                break

        return claims

    def _record_failure(
        self,
        db: Session,
        *,
        state_id: UUID,
        run_id: UUID,
        attempt_number: int,
        failure_time: datetime,
        exc: Exception,
    ) -> None:
        delay = min(
            self.retry_max_seconds,
            self.retry_base_seconds
            * (
                2
                ** max(
                    attempt_number - 1,
                    0,
                )
            ),
        )

        try:
            self.processing_repository.fail(
                db,
                state_id=state_id,
                run_id=run_id,
                worker_id=self.worker_id,
                now=failure_time,
                retry_after=(
                    failure_time
                    + timedelta(seconds=delay)
                ),
                error_code=type(exc).__name__,
                error_message=str(exc)[:2000],
            )

        except ArticleProcessingLeaseLostError:
            self.processing_repository.mark_lease_lost(
                db,
                run_id=run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired while "
                    "handling normalization failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> ArticleNormalizationBatchResult:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        changed = 0
        unchanged = 0

        with self.session_factory() as db:
            claim_now = self.clock()

            with db.begin():
                claims = self._claim_pending(
                    db,
                    limit=limit,
                    now=claim_now,
                )

            for claim in claims:
                try:
                    with db.begin():
                        article = db.scalar(
                            select(Article).where(
                                Article.id == claim.article_id,
                                Article.deleted_at.is_(None),
                            )
                        )

                        if article is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason=(
                                    "article became ineligible "
                                    "after normalization claim"
                                ),
                            )
                            continue

                        article_changed = (
                            self.service.normalize_article(
                                article
                            )
                        )

                        finalization_time = self.clock()

                        lease_valid = (
                            self.processing_repository.heartbeat(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=finalization_time,
                                claim_expires_at=(
                                    finalization_time
                                    + timedelta(
                                        seconds=self.claim_ttl_seconds
                                    )
                                ),
                            )
                        )

                        if not lease_valid:
                            raise ArticleProcessingLeaseLostError(
                                "processing lease is no longer valid"
                            )

                        self.processing_repository.complete(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=self.clock(),
                        )

                    if article_changed:
                        changed += 1
                    else:
                        unchanged += 1

                except ArticleProcessingLeaseLostError as exc:
                    db.rollback()

                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=claim.run_id,
                            now=self.clock(),
                            error_message=str(exc),
                        )

                except Exception as exc:
                    db.rollback()

                    failure_time = self.clock()

                    with db.begin():
                        self._record_failure(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            attempt_number=claim.attempt_number,
                            failure_time=failure_time,
                            exc=exc,
                        )

                    logger.exception(
                        "Article normalization failed",
                        extra={
                            "article_id": str(claim.article_id),
                            "processing_run_id": str(claim.run_id),
                        },
                    )

        return ArticleNormalizationBatchResult(
            processed=changed + unchanged,
            changed=changed,
            unchanged=unchanged,
        )