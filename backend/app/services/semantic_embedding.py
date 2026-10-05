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

from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.article_processing import ArticleProcessingState
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.semantic.provider import EmbeddingProvider, EmbeddingVector


logger = logging.getLogger(__name__)


class SemanticEmbeddingInputChangedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedClaimEmbedding:
    claim_id: UUID
    input_hash: str
    text: str


@dataclass(frozen=True, slots=True)
class PreparedSemanticEmbedding:
    article_id: UUID
    expected_hash: str
    article_input_hash: str
    article_text: str | None
    claims: tuple[PreparedClaimEmbedding, ...]


@dataclass(frozen=True, slots=True)
class SemanticEmbeddingBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


class SemanticEmbeddingService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        max_article_characters: int = 12000,
        include_article_embeddings: bool = True,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        if max_article_characters <= 0:
            raise ValueError(
                "max_article_characters must be greater than zero"
            )
        if not config_version:
            raise ValueError("config_version must not be empty")

        self.provider = provider
        self.max_article_characters = max_article_characters
        self.include_article_embeddings = include_article_embeddings
        self.config_version = config_version

    @property
    def processing_configuration_version(self) -> str:
        payload = {
            "base_version": self.config_version,
            "model": self.provider.model,
            "dimensions": getattr(self.provider, "dimensions", None),
            "max_article_characters": self.max_article_characters,
            "include_article_embeddings": self.include_article_embeddings,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def load_active_claims(
        db: Session,
        article_ids: list[UUID],
    ) -> dict[UUID, tuple[ArticleClaim, ...]]:
        result: dict[UUID, list[ArticleClaim]] = {
            article_id: []
            for article_id in article_ids
        }
        if not article_ids:
            return {}

        rows = db.scalars(
            select(ArticleClaim)
            .where(
                ArticleClaim.article_id.in_(article_ids),
                ArticleClaim.deleted_at.is_(None),
            )
            .order_by(
                ArticleClaim.article_id,
                ArticleClaim.text_source,
                ArticleClaim.sentence_index,
                ArticleClaim.start_offset,
                ArticleClaim.id,
            )
        ).all()

        for claim in rows:
            result.setdefault(claim.article_id, []).append(claim)

        return {
            article_id: tuple(claims)
            for article_id, claims in result.items()
        }

    def input_hash(
        self,
        article: Article,
        claims: tuple[ArticleClaim, ...],
    ) -> str:
        payload = {
            "article_id": str(article.id),
            "content_hash": article.content_hash or "",
            "language_code": article.language_code or "",
            "claims": [
                [str(claim.id), claim.claim_hash]
                for claim in claims
            ],
            "model": self.provider.model,
            "configuration": self.processing_configuration_version,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def candidate(
        self,
        article: Article,
        claims: tuple[ArticleClaim, ...],
    ) -> ArticleProcessingCandidate:
        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.input_hash(article, claims),
            provider=self.provider.provider,
            provider_version=self.provider.version,
            configuration_version=self.processing_configuration_version,
        )

    def _article_text(self, article: Article) -> str:
        title = (
            article.normalized_title
            or article.title
            or ""
        ).strip()
        body = (article.normalized_text or "").strip()

        if title and body:
            value = f"{title}\n\n{body}"
        else:
            value = title or body

        return value[: self.max_article_characters]

    def prepare(
        self,
        article: Article,
        claims: tuple[ArticleClaim, ...],
    ) -> PreparedSemanticEmbedding:
        article_input_hash = article.content_hash or ""
        expected_dimensions = getattr(self.provider, "dimensions", None)
        article_stale = self.include_article_embeddings and (
            not article.semantic_embedding
            or article.semantic_model != self.provider.model
            or article.semantic_input_hash != article_input_hash
            or (
                expected_dimensions is not None
                and len(article.semantic_embedding) != expected_dimensions
            )
        )

        prepared_claims = tuple(
            PreparedClaimEmbedding(
                claim_id=claim.id,
                input_hash=claim.claim_hash,
                text=claim.claim_text,
            )
            for claim in claims
            if (
                not claim.semantic_embedding
                or claim.semantic_model != self.provider.model
                or claim.semantic_input_hash != claim.claim_hash
                or (
                    expected_dimensions is not None
                    and len(claim.semantic_embedding) != expected_dimensions
                )
            )
        )

        return PreparedSemanticEmbedding(
            article_id=article.id,
            expected_hash=self.input_hash(article, claims),
            article_input_hash=article_input_hash,
            article_text=(
                self._article_text(article)
                if article_stale
                else None
            ),
            claims=prepared_claims,
        )

    @staticmethod
    def request_character_count(
        prepared: PreparedSemanticEmbedding,
    ) -> int:
        return (
            len(prepared.article_text or "")
            + sum(len(claim.text) for claim in prepared.claims)
        )

    def embed_batch(
        self,
        prepared_items: tuple[PreparedSemanticEmbedding, ...],
    ) -> dict[
        UUID,
        tuple[
            EmbeddingVector | None,
            dict[UUID, EmbeddingVector],
        ],
    ]:
        texts: list[str] = []
        article_indexes: dict[UUID, int] = {}
        claim_indexes: dict[UUID, dict[UUID, int]] = {}
        seen_articles: set[UUID] = set()

        for prepared in prepared_items:
            if prepared.article_id in seen_articles:
                raise ValueError(
                    "semantic embedding batch contains duplicate article ids"
                )
            seen_articles.add(prepared.article_id)

            if prepared.article_text is not None:
                article_indexes[prepared.article_id] = len(texts)
                texts.append(prepared.article_text)

            per_article_claims: dict[UUID, int] = {}
            for claim in prepared.claims:
                per_article_claims[claim.claim_id] = len(texts)
                texts.append(claim.text)
            claim_indexes[prepared.article_id] = per_article_claims

        if texts:
            vectors = self.provider.embed(tuple(texts))
            if len(vectors) != len(texts):
                raise ValueError(
                    "embedding provider result count does not match inputs"
                )
        else:
            vectors = ()

        result: dict[
            UUID,
            tuple[
                EmbeddingVector | None,
                dict[UUID, EmbeddingVector],
            ],
        ] = {}
        for prepared in prepared_items:
            article_index = article_indexes.get(prepared.article_id)
            article_vector = (
                vectors[article_index]
                if article_index is not None
                else None
            )
            result[prepared.article_id] = (
                article_vector,
                {
                    claim_id: vectors[index]
                    for claim_id, index in claim_indexes[
                        prepared.article_id
                    ].items()
                },
            )

        return result

    def embed(
        self,
        prepared: PreparedSemanticEmbedding,
    ) -> tuple[
        EmbeddingVector | None,
        dict[UUID, EmbeddingVector],
    ]:
        return self.embed_batch((prepared,))[prepared.article_id]


class SemanticEmbeddingRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: SemanticEmbeddingService,
        processing_repository: ArticleProcessingRepository | None = None,
        *,
        claim_ttl_seconds: float = 300,
        retry_base_seconds: float = 30,
        retry_max_seconds: float = 3600,
        max_batch_characters: int = 24000,
        live_claim_fraction: float = 0.8,
        worker_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            claim_ttl_seconds <= 0
            or retry_base_seconds <= 0
            or retry_max_seconds < retry_base_seconds
            or max_batch_characters <= 0
            or not 0 < live_claim_fraction < 1
        ):
            raise ValueError("semantic embedding runner settings are invalid")

        self.session_factory = session_factory
        self.service = service
        self.processing_repository = (
            processing_repository
            or ArticleProcessingRepository()
        )
        self.claim_ttl_seconds = claim_ttl_seconds
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self.max_batch_characters = max_batch_characters
        self.live_claim_fraction = live_claim_fraction
        self.worker_id = worker_id or str(uuid4())
        self.clock = clock or (lambda: datetime.now(UTC))

    def _eligible_article(
        self,
        db: Session,
        article_id: UUID,
        *,
        for_update: bool = False,
    ) -> Article | None:
        statement = (
            select(Article)
            .join(Feed)
            .join(Source)
            .where(
                Article.id == article_id,
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update(of=Article)
        return db.scalar(statement)

    def _claim_pending_pool(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
        processed: bool,
        excluded_article_ids: set[UUID] | None = None,
    ) -> list[ArticleProcessingClaim]:
        if limit <= 0:
            return []

        claims: list[ArticleProcessingClaim] = []
        excluded_article_ids = excluded_article_ids or set()
        page_size = max(100, limit * 4)
        last_created_at = None
        last_article_id = None

        state_join = and_(
            ArticleProcessingState.article_id == Article.id,
            ArticleProcessingState.pipeline
            == ArticlePipeline.SEMANTIC_EMBEDDING.value,
            ArticleProcessingState.deleted_at.is_(None),
        )

        while len(claims) < limit:
            conditions = [
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            ]

            if processed:
                conditions.append(
                    ArticleProcessingState.processed_input_hash.is_not(None)
                )
            else:
                conditions.append(
                    or_(
                        ArticleProcessingState.id.is_(None),
                        ArticleProcessingState.processed_input_hash.is_(None),
                    )
                )

            if excluded_article_ids:
                conditions.append(
                    Article.id.not_in(excluded_article_ids)
                )

            if (
                last_created_at is not None
                and last_article_id is not None
            ):
                if processed:
                    page_condition = or_(
                        Article.created_at > last_created_at,
                        and_(
                            Article.created_at == last_created_at,
                            Article.id > last_article_id,
                        ),
                    )
                else:
                    page_condition = or_(
                        Article.created_at < last_created_at,
                        and_(
                            Article.created_at == last_created_at,
                            Article.id < last_article_id,
                        ),
                    )
                conditions.append(page_condition)

            order_by = (
                (Article.created_at, Article.id)
                if processed
                else (
                    Article.created_at.desc(),
                    Article.id.desc(),
                )
            )

            articles = list(
                db.scalars(
                    select(Article)
                    .join(Feed)
                    .join(Source)
                    .outerjoin(
                        ArticleProcessingState,
                        state_join,
                    )
                    .where(*conditions)
                    .order_by(*order_by)
                    .limit(page_size)
                ).all()
            )
            if not articles:
                break

            remaining = limit - len(claims)
            candidate_articles = articles[:remaining]
            claims_by_article = self.service.load_active_claims(
                db,
                [article.id for article in candidate_articles],
            )
            candidates = [
                self.service.candidate(
                    article,
                    claims_by_article.get(article.id, ()),
                )
                for article in candidate_articles
            ]
            claims.extend(
                self.processing_repository.claim_candidates(
                    db,
                    pipeline=ArticlePipeline.SEMANTIC_EMBEDDING.value,
                    candidates=candidates,
                    worker_id=self.worker_id,
                    now=now,
                    claim_expires_at=(
                        now
                        + timedelta(seconds=self.claim_ttl_seconds)
                    ),
                    limit=remaining,
                )
            )

            last_article = candidate_articles[-1]
            last_created_at = last_article.created_at
            last_article_id = last_article.id
            if (
                len(articles) < page_size
                and len(candidate_articles) == len(articles)
            ):
                break

        return claims

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[ArticleProcessingClaim]:
        if limit <= 0:
            return []

        live_limit = (
            limit
            if limit == 1
            else max(
                1,
                int(limit * self.live_claim_fraction),
            )
        )

        claims = self._claim_pending_pool(
            db,
            limit=live_limit,
            now=now,
            processed=False,
        )
        claimed_article_ids = {
            claim.article_id
            for claim in claims
        }

        backfill_limit = limit - len(claims)
        backfill_claims = self._claim_pending_pool(
            db,
            limit=backfill_limit,
            now=now,
            processed=True,
            excluded_article_ids=claimed_article_ids,
        )
        claims.extend(backfill_claims)
        claimed_article_ids.update(
            claim.article_id
            for claim in backfill_claims
        )

        remaining = limit - len(claims)
        if remaining > 0:
            claims.extend(
                self._claim_pending_pool(
                    db,
                    limit=remaining,
                    now=now,
                    processed=False,
                    excluded_article_ids=claimed_article_ids,
                )
            )

        return claims

    def _record_failure(
        self,
        db: Session,
        *,
        claim: ArticleProcessingClaim,
        failure_time: datetime,
        exc: Exception,
    ) -> None:
        delay = min(
            self.retry_max_seconds,
            self.retry_base_seconds
            * (2 ** max(claim.attempt_number - 1, 0)),
        )
        try:
            self.processing_repository.fail(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id=self.worker_id,
                now=failure_time,
                retry_after=(
                    failure_time + timedelta(seconds=delay)
                ),
                error_code=type(exc).__name__,
                error_message=str(exc)[:2000],
            )
        except ArticleProcessingLeaseLostError:
            self.processing_repository.mark_lease_lost(
                db,
                run_id=claim.run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired while handling "
                    "semantic embedding failure"
                ),
            )

    def _bounded_batch(
        self,
        prepared_items: list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ],
    ) -> tuple[
        list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ],
        list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ],
    ]:
        selected: list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ] = []
        used_characters = 0

        for index, item in enumerate(prepared_items):
            _, prepared = item
            item_characters = self.service.request_character_count(
                prepared
            )
            if (
                selected
                and used_characters + item_characters
                > self.max_batch_characters
            ):
                return selected, prepared_items[index:]

            selected.append(item)
            used_characters += item_characters

        return selected, []

    def _defer_batch_items(
        self,
        db: Session,
        items: list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ],
    ) -> int:
        deferred = 0
        for claim, _ in items:
            try:
                with db.begin():
                    self.processing_repository.skip(
                        db,
                        state_id=claim.state_id,
                        run_id=claim.run_id,
                        worker_id=self.worker_id,
                        now=self.clock(),
                        reason=(
                            "deferred by semantic embedding "
                            "batch character budget"
                        ),
                    )
                deferred += 1
            except ArticleProcessingLeaseLostError:
                db.rollback()
                with db.begin():
                    self.processing_repository.mark_lease_lost(
                        db,
                        run_id=claim.run_id,
                        now=self.clock(),
                        error_message=(
                            "processing lease expired while deferring "
                            "semantic embedding batch item"
                        ),
                    )
                deferred += 1
        return deferred

    def _record_batch_failure(
        self,
        db: Session,
        *,
        items: list[
            tuple[
                ArticleProcessingClaim,
                PreparedSemanticEmbedding,
            ]
        ],
        exc: Exception,
    ) -> int:
        failed = 0
        for claim, _ in items:
            db.rollback()
            failure_time = self.clock()
            with db.begin():
                self._record_failure(
                    db,
                    claim=claim,
                    failure_time=failure_time,
                    exc=exc,
                )
            failed += 1
        return failed

    def run_pending(
        self,
        *,
        limit: int,
    ) -> SemanticEmbeddingBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        processed = 0
        skipped = 0
        failed = 0

        with self.session_factory() as db:
            claim_now = self.clock()
            with db.begin():
                claims = self._claim_pending(
                    db,
                    limit=limit,
                    now=claim_now,
                )

            prepared_items: list[
                tuple[
                    ArticleProcessingClaim,
                    PreparedSemanticEmbedding,
                ]
            ] = []

            for claim in claims:
                try:
                    with db.begin():
                        article = self._eligible_article(
                            db,
                            claim.article_id,
                            for_update=True,
                        )
                        if article is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason=(
                                    "article became ineligible after "
                                    "semantic embedding claim"
                                ),
                            )
                            skipped += 1
                            continue

                        active_claims = self.service.load_active_claims(
                            db,
                            [article.id],
                        ).get(article.id, ())
                        current_candidate = self.service.candidate(
                            article,
                            active_claims,
                        )
                        if not claim.matches_candidate(
                            current_candidate
                        ):
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason=(
                                    "semantic embedding input changed "
                                    "after claim"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared_items.append(
                            (
                                claim,
                                self.service.prepare(
                                    article,
                                    active_claims,
                                ),
                            )
                        )

                except ArticleProcessingLeaseLostError as exc:
                    db.rollback()
                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=claim.run_id,
                            now=self.clock(),
                            error_message=str(exc),
                        )
                    skipped += 1

                except Exception as exc:
                    db.rollback()
                    failure_time = self.clock()
                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=failure_time,
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Semantic embedding preparation failed",
                        extra={
                            "article_id": str(claim.article_id),
                            "provider": (
                                self.service.provider.provider
                            ),
                            "model": self.service.provider.model,
                            "processing_run_id": str(claim.run_id),
                        },
                    )

            batch_items, deferred_items = self._bounded_batch(
                prepared_items
            )
            skipped += self._defer_batch_items(
                db,
                deferred_items,
            )

            if batch_items:
                try:
                    vectors_by_article = self.service.embed_batch(
                        tuple(
                            prepared
                            for _, prepared in batch_items
                        )
                    )
                except Exception as exc:
                    failed += self._record_batch_failure(
                        db,
                        items=batch_items,
                        exc=exc,
                    )
                    logger.exception(
                        "Semantic embedding provider batch failed",
                        extra={
                            "article_count": len(batch_items),
                            "provider": self.service.provider.provider,
                            "model": self.service.provider.model,
                        },
                    )
                    batch_items = []
                    vectors_by_article = {}
            else:
                vectors_by_article = {}

            for claim, prepared in batch_items:
                try:
                    (
                        article_vector,
                        claim_vectors,
                    ) = vectors_by_article[prepared.article_id]

                    with db.begin():
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

                        article = self._eligible_article(
                            db,
                            claim.article_id,
                            for_update=True,
                        )
                        if article is None:
                            raise SemanticEmbeddingInputChangedError(
                                "article became ineligible before persistence"
                            )

                        active_claims = self.service.load_active_claims(
                            db,
                            [article.id],
                        ).get(article.id, ())
                        if (
                            self.service.input_hash(
                                article,
                                active_claims,
                            )
                            != prepared.expected_hash
                        ):
                            raise SemanticEmbeddingInputChangedError(
                                "semantic embedding input changed "
                                "before persistence"
                            )

                        if article_vector is not None:
                            article.semantic_embedding = list(
                                article_vector
                            )
                            article.semantic_model = (
                                self.service.provider.model
                            )
                            article.semantic_input_hash = (
                                prepared.article_input_hash
                            )
                            article.semantic_embedded_at = (
                                finalization_time
                            )

                        claims_by_id = {
                            item.id: item
                            for item in active_claims
                        }
                        prepared_by_id = {
                            item.claim_id: item
                            for item in prepared.claims
                        }
                        for claim_id, vector in claim_vectors.items():
                            current = claims_by_id.get(claim_id)
                            prepared_claim = prepared_by_id.get(
                                claim_id
                            )
                            if (
                                current is None
                                or prepared_claim is None
                                or current.claim_hash
                                != prepared_claim.input_hash
                            ):
                                raise SemanticEmbeddingInputChangedError(
                                    "claim changed before semantic "
                                    "embedding persistence"
                                )
                            current.semantic_embedding = list(vector)
                            current.semantic_model = (
                                self.service.provider.model
                            )
                            current.semantic_input_hash = (
                                prepared_claim.input_hash
                            )
                            current.semantic_embedded_at = (
                                finalization_time
                            )

                        self.processing_repository.complete(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=self.clock(),
                        )

                    processed += 1

                except SemanticEmbeddingInputChangedError:
                    db.rollback()
                    with db.begin():
                        self.processing_repository.skip(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=self.clock(),
                            reason=(
                                "semantic embedding input changed "
                                "during processing"
                            ),
                        )
                    skipped += 1

                except ArticleProcessingLeaseLostError as exc:
                    db.rollback()
                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=claim.run_id,
                            now=self.clock(),
                            error_message=str(exc),
                        )
                    skipped += 1

                except Exception as exc:
                    db.rollback()
                    failure_time = self.clock()
                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=failure_time,
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Semantic embedding persistence failed",
                        extra={
                            "article_id": str(claim.article_id),
                            "provider": (
                                self.service.provider.provider
                            ),
                            "model": self.service.provider.model,
                            "processing_run_id": str(claim.run_id),
                        },
                    )

        return SemanticEmbeddingBatchResult(
            selected=len(claims),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
