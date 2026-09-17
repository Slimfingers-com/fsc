from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.feed import Feed
from app.models.search_document import SearchDocument
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.repositories.search_document import SearchDocumentRepository
from app.search.builder import SearchDocumentBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchIndexBatchResult:
    processed: int
    created: int
    updated: int
    deleted: int = 0


class SearchIndexingService:
    PROVIDER = "search_document_builder"
    CONFIG_VERSION = "1"

    def __init__(
        self,
        repository: SearchDocumentRepository | None = None,
        builder: SearchDocumentBuilder | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.repository = repository or SearchDocumentRepository()
        self.builder = builder or SearchDocumentBuilder()
        self.config_version = config_version

    @property
    def provider_version(self) -> str:
        return str(self.builder.VERSION)

    def candidate(
        self,
        article: Article,
    ) -> ArticleProcessingCandidate:
        if article.id is None:
            raise ValueError(
                "article must be persisted before indexing"
            )

        data = self.builder.build(article)

        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=data.document_hash,
            provider=self.PROVIDER,
            provider_version=self.provider_version,
            configuration_version=self.config_version,
        )

    def index_article(
        self,
        db: Session,
        article: Article,
    ) -> bool:
        data = self.builder.build(article)

        document = self.repository.get_by_article_id(
            db,
            data.article_id,
            include_deleted=True,
        )

        values = asdict(data)

        if (
            document is not None
            and document.deleted_at is not None
        ):
            self.repository.hard_delete(
                db,
                document,
            )
            db.flush()
            document = None

        if document is None:
            self.repository.add(
                db,
                SearchDocument(**values),
            )
            return True

        for key, value in values.items():
            setattr(
                document,
                key,
                value,
            )

        return False


class SearchIndexingRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: SearchIndexingService | None = None,
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
        self.service = service or SearchIndexingService()
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

        last_normalized_at = None
        last_article_id = None

        while len(claims) < limit:
            conditions = [
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.content_hash.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            ]

            if (
                last_normalized_at is not None
                and last_article_id is not None
            ):
                conditions.append(
                    or_(
                        Article.normalized_at
                        > last_normalized_at,
                        and_(
                            Article.normalized_at
                            == last_normalized_at,
                            Article.id
                            > last_article_id,
                        ),
                    )
                )

            articles = list(
                db.scalars(
                    select(Article)
                    .join(Article.feed)
                    .join(Feed.source)
                    .where(*conditions)
                    .options(
                        joinedload(
                            Article.feed
                        ).joinedload(
                            Feed.source
                        )
                    )
                    .order_by(
                        Article.normalized_at,
                        Article.id,
                    )
                    .limit(page_size)
                )
                .unique()
                .all()
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
                    pipeline=ArticlePipeline.SEARCH_INDEXING.value,
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
            last_normalized_at = last_article.normalized_at
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
                    "handling search indexing failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> SearchIndexBatchResult:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        created = 0
        updated = 0

        with self.session_factory() as db:
            claim_now = self.clock()

            with db.begin():
                deleted_article_ids = (
                    self.service.repository
                    .delete_ineligible(db)
                )

                self.processing_repository.invalidate_processed(
                    db,
                    pipeline=ArticlePipeline.SEARCH_INDEXING.value,
                    article_ids=deleted_article_ids,
                )

                claims = self._claim_pending(
                    db,
                    limit=limit,
                    now=claim_now,
                )

            for claim in claims:
                try:
                    with db.begin():
                        article = db.scalar(
                            select(Article)
                            .join(Article.feed)
                            .join(Feed.source)
                            .where(
                                Article.id == claim.article_id,
                                Article.deleted_at.is_(None),
                                Article.normalized_at.is_not(None),
                                Article.content_hash.is_not(None),
                                Feed.deleted_at.is_(None),
                                Feed.active.is_(True),
                                Source.deleted_at.is_(None),
                                Source.active.is_(True),
                            )
                            .options(
                                joinedload(
                                    Article.feed
                                ).joinedload(
                                    Feed.source
                                )
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
                                    "after search indexing claim"
                                ),
                            )
                            continue

                        was_created = (
                            self.service.index_article(
                                db,
                                article,
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

                    if was_created:
                        created += 1
                    else:
                        updated += 1

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
                        "Search indexing failed",
                        extra={
                            "article_id": str(claim.article_id),
                            "processing_run_id": str(claim.run_id),
                        },
                    )

        return SearchIndexBatchResult(
            processed=created + updated,
            created=created,
            updated=updated,
            deleted=len(deleted_article_ids),
        )