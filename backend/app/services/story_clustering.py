import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.clustering.features import (
    TITLE_FEATURE_VERSION,
    extract_title_terms,
)
from app.clustering.provider import (
    StoryCandidate,
    StoryClusterer,
    StoryClusteringInput,
    StoryClusteringResult,
)
from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.repositories.story import StoryRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedStoryClustering:
    article_title: str | None
    article: StoryClusteringInput
    candidates: tuple[StoryCandidate, ...]


@dataclass(frozen=True, slots=True)
class AppliedStoryClustering:
    story_id: UUID
    membership_id: UUID
    changed: bool
    match_kind: str


@dataclass(frozen=True, slots=True)
class StoryClusteringBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


class StoryClusteringService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        *,
        clusterer: StoryClusterer,
        repository: StoryRepository | None = None,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        if not config_version:
            raise ValueError(
                "config_version must not be empty"
            )

        self.clusterer = clusterer
        self.repository = repository or StoryRepository()
        self.config_version = config_version

    def processing_configuration_version(
        self,
        *,
        window_hours: float,
        candidate_limit: int,
    ) -> str:
        if window_hours <= 0:
            raise ValueError(
                "window_hours must be greater than zero"
            )

        if candidate_limit <= 0:
            raise ValueError(
                "candidate_limit must be greater than zero"
            )

        payload = {
            "service_config_version": self.config_version,
            "title_feature_version": TITLE_FEATURE_VERSION,
            "clusterer_configuration": (
                self.clusterer.configuration()
            ),
            "window_hours": window_hours,
            "candidate_limit": candidate_limit,
        }

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def clustering_hash(
        self,
        article: Article,
        *,
        entity_ids: tuple[UUID, ...],
        topic_ids: tuple[UUID, ...],
    ) -> str:
        feature_title = (
            article.normalized_title
            or article.title
        )

        article_time = (
            article.published_at
            or article.created_at
        )

        payload = {
            "article_title": article.title or "",
            "article_time": article_time.isoformat(),
            "language_code": article.language_code or "",
            "title_feature_version": TITLE_FEATURE_VERSION,
            "title_terms": list(
                extract_title_terms(
                    feature_title
                )
            ),
            "entity_ids": [
                str(value)
                for value in sorted(
                    entity_ids,
                    key=str,
                )
            ],
            "topic_ids": [
                str(value)
                for value in sorted(
                    topic_ids,
                    key=str,
                )
            ],
        }

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def candidate(
        self,
        article: Article,
        *,
        entity_ids: tuple[UUID, ...],
        topic_ids: tuple[UUID, ...],
        window_hours: float,
        candidate_limit: int,
    ) -> ArticleProcessingCandidate:
        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.clustering_hash(
                article,
                entity_ids=entity_ids,
                topic_ids=topic_ids,
            ),
            provider=self.clusterer.provider,
            provider_version=self.clusterer.version,
            configuration_version=(
                self.processing_configuration_version(
                    window_hours=window_hours,
                    candidate_limit=candidate_limit,
                )
            ),
        )

    def prepare(
        self,
        db: Session,
        *,
        article_id: UUID,
        window_hours: float,
        candidate_limit: int,
    ) -> PreparedStoryClustering | None:
        article = db.scalar(
            select(Article)
            .join(
                Feed,
                Feed.id == Article.feed_id,
            )
            .join(
                Source,
                Source.id == Feed.source_id,
            )
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
        )

        if article is None:
            return None

        entity_ids_by_article, topic_ids_by_article = (
            self.repository.load_feature_ids(
                db,
                [article.id],
            )
        )

        feature_title = (
            article.normalized_title
            or article.title
        )

        clustering_input = StoryClusteringInput(
            article_id=article.id,
            language_code=article.language_code,
            article_time=(
                article.published_at
                or article.created_at
            ),
            title_terms=extract_title_terms(
                feature_title
            ),
            entity_ids=entity_ids_by_article[
                article.id
            ],
            topic_ids=topic_ids_by_article[
                article.id
            ],
        )

        candidates = self.repository.list_candidates(
            db,
            article=clustering_input,
            window_hours=window_hours,
            limit=candidate_limit,
        )

        return PreparedStoryClustering(
            article_title=article.title,
            article=clustering_input,
            candidates=candidates,
        )

    def cluster(
        self,
        prepared: PreparedStoryClustering,
    ) -> StoryClusteringResult:
        return self.clusterer.cluster(
            prepared.article,
            prepared.candidates,
        )

    def cluster_article(
        self,
        db: Session,
        *,
        article_id: UUID,
        processing_run_id: UUID,
        clustered_at: datetime,
        window_hours: float,
        candidate_limit: int,
    ) -> AppliedStoryClustering | None:
        self.repository.acquire_clustering_lock(db)

        prepared = self.prepare(
            db,
            article_id=article_id,
            window_hours=window_hours,
            candidate_limit=candidate_limit,
        )

        if prepared is None:
            return None

        result = self.cluster(prepared)

        self._validate_result(
            prepared,
            result,
        )

        return self._apply_result_locked(
            db,
            prepared=prepared,
            result=result,
            processing_run_id=processing_run_id,
            clustered_at=clustered_at,
        )

    def apply_result(
        self,
        db: Session,
        *,
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
        processing_run_id: UUID,
        clustered_at: datetime,
    ) -> AppliedStoryClustering:
        self._validate_result(
            prepared,
            result,
        )

        self.repository.acquire_clustering_lock(db)

        return self._apply_result_locked(
            db,
            prepared=prepared,
            result=result,
            processing_run_id=processing_run_id,
            clustered_at=clustered_at,
        )

    @staticmethod
    def _validate_result(
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
    ) -> None:
        if not 0.0 <= result.similarity_score <= 1.0:
            raise ValueError(
                "similarity_score must be between zero and one"
            )

        if result.story_id is None:
            return

        candidate_story_ids = {
            candidate.story_id
            for candidate in prepared.candidates
        }

        if result.story_id not in candidate_story_ids:
            raise ValueError(
                "clusterer returned a story "
                "outside the candidate set"
            )

    def _apply_result_locked(
        self,
        db: Session,
        *,
        prepared: PreparedStoryClustering,
        result: StoryClusteringResult,
        processing_run_id: UUID,
        clustered_at: datetime,
    ) -> AppliedStoryClustering:
        existing_run_membership = (
            self.repository.get_membership_by_processing_run(
                db,
                processing_run_id,
            )
        )

        if existing_run_membership is not None:
            return AppliedStoryClustering(
                story_id=existing_run_membership.story_id,
                membership_id=existing_run_membership.id,
                changed=False,
                match_kind=existing_run_membership.match_kind,
            )

        existing = self.repository.get_active_membership(
            db,
            prepared.article.article_id,
            for_update=True,
        )

        if result.story_id is None:
            target_story = self.repository.create_story(
                db,
                language_code=(
                    prepared.article.language_code
                ),
            )
            target_story_id = target_story.id
            match_kind = "created"
        else:
            target_story = self.repository.get_story(
                db,
                result.story_id,
                for_update=True,
            )

            if target_story is None:
                raise ValueError(
                    "clusterer target story is not active"
                )

            if (
                target_story.language_code
                != prepared.article.language_code
            ):
                raise ValueError(
                    "clusterer target story language "
                    "does not match article language"
                )

            target_story_id = target_story.id

            if (
                existing is not None
                and existing.story_id
                == target_story_id
            ):
                match_kind = "retained"
            else:
                match_kind = "matched"

        match_details = self._build_match_details(
            result
        )

        membership = self.repository.replace_membership(
            db,
            story_id=target_story_id,
            article_id=prepared.article.article_id,
            processing_run_id=processing_run_id,
            article_title=prepared.article_title,
            article_time=prepared.article.article_time,
            title_terms=prepared.article.title_terms,
            entity_ids=prepared.article.entity_ids,
            topic_ids=prepared.article.topic_ids,
            similarity_score=result.similarity_score,
            match_kind=match_kind,
            match_details=match_details,
            clustered_at=clustered_at,
        )

        return AppliedStoryClustering(
            story_id=membership.story_id,
            membership_id=membership.id,
            changed=True,
            match_kind=membership.match_kind,
        )

    @staticmethod
    def _build_match_details(
        result: StoryClusteringResult,
    ) -> dict[str, object]:
        details = dict(result.details)

        details["matched_membership_id"] = (
            str(result.matched_membership_id)
            if result.matched_membership_id
            is not None
            else None
        )
        details["matched_article_id"] = (
            str(result.matched_article_id)
            if result.matched_article_id
            is not None
            else None
        )

        return details

class StoryClusteringRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: StoryClusteringService,
        processing_repository: ArticleProcessingRepository | None = None,
        *,
        claim_ttl_seconds: float = 300,
        retry_base_seconds: float = 30,
        retry_max_seconds: float = 3600,
        window_hours: float,
        candidate_limit: int,
        worker_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            claim_ttl_seconds <= 0
            or retry_base_seconds <= 0
            or retry_max_seconds < retry_base_seconds
            or window_hours <= 0
            or candidate_limit <= 0
        ):
            raise ValueError(
                "story clustering runner settings are invalid"
            )

        self.session_factory = session_factory
        self.service = service
        self.processing_repository = (
            processing_repository
            or ArticleProcessingRepository()
        )

        self.claim_ttl_seconds = claim_ttl_seconds
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self.window_hours = window_hours
        self.candidate_limit = candidate_limit

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
                Article.normalized_at.is_not(None),
                Article.normalized_text.is_not(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            ]

            if (
                last_created_at is not None
                and last_article_id is not None
            ):
                conditions.append(
                    or_(
                        Article.created_at
                        > last_created_at,
                        and_(
                            Article.created_at
                            == last_created_at,
                            Article.id
                            > last_article_id,
                        ),
                    )
                )

            articles = list(
                db.scalars(
                    select(Article)
                    .join(Feed)
                    .join(Source)
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

            article_ids = [
                article.id
                for article in articles
            ]

            (
                entity_ids_by_article,
                topic_ids_by_article,
            ) = self.service.repository.load_feature_ids(
                db,
                article_ids,
            )

            candidates = [
                self.service.candidate(
                    article,
                    entity_ids=(
                        entity_ids_by_article[
                            article.id
                        ]
                    ),
                    topic_ids=(
                        topic_ids_by_article[
                            article.id
                        ]
                    ),
                    window_hours=self.window_hours,
                    candidate_limit=self.candidate_limit,
                )
                for article in articles
            ]

            remaining = limit - len(claims)

            claims.extend(
                self.processing_repository.claim_candidates(
                    db,
                    pipeline=(
                        ArticlePipeline
                        .STORY_CLUSTERING
                        .value
                    ),
                    candidates=candidates,
                    worker_id=self.worker_id,
                    now=now,
                    claim_expires_at=(
                        now
                        + timedelta(
                            seconds=(
                                self.claim_ttl_seconds
                            )
                        )
                    ),
                    limit=remaining,
                )
            )

            last_article = articles[-1]
            last_created_at = (
                last_article.created_at
            )
            last_article_id = (
                last_article.id
            )

            if len(articles) < page_size:
                break

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
            * (
                2
                ** max(
                    claim.attempt_number - 1,
                    0,
                )
            ),
        )

        try:
            self.processing_repository.fail(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id=self.worker_id,
                now=failure_time,
                retry_after=(
                    failure_time
                    + timedelta(
                        seconds=delay
                    )
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
                    "processing lease expired while "
                    "handling story clustering failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> StoryClusteringBatchResult:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

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

            for claim in claims:
                try:
                    with db.begin():
                        processing_time = self.clock()

                        lease_valid = (
                            self.processing_repository
                            .heartbeat(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=processing_time,
                                claim_expires_at=(
                                    processing_time
                                    + timedelta(
                                        seconds=(
                                            self.claim_ttl_seconds
                                        )
                                    )
                                ),
                            )
                        )

                        if not lease_valid:
                            raise ArticleProcessingLeaseLostError(
                                "processing lease is no longer valid"
                            )

                        applied = self.service.cluster_article(
                            db,
                            article_id=claim.article_id,
                            processing_run_id=claim.run_id,
                            clustered_at=processing_time,
                            window_hours=self.window_hours,
                            candidate_limit=self.candidate_limit,
                        )

                        if applied is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason=(
                                    "article became ineligible "
                                    "after story clustering claim"
                                ),
                            )
                            skipped += 1
                            continue

                        self.processing_repository.complete(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=self.clock(),
                        )

                    processed += 1

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
                        "Story clustering failed",
                        extra={
                            "article_id": str(
                                claim.article_id
                            ),
                            "provider": (
                                self.service
                                .clusterer
                                .provider
                            ),
                            "version": (
                                self.service
                                .clusterer
                                .version
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                        },
                    )

        return StoryClusteringBatchResult(
            selected=len(claims),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
