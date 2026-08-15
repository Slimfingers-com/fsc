import hashlib
import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.normalization import normalize_name
from app.analysis.provider import (
    AnalysisResult,
    ArticleAnalysisInput,
    EntityTopicAnalyzer,
    EntityType,
    TextPart,
)
from app.analysis.resolver import EntityResolver, TopicResolver
from app.analysis.rule_based import RuleBasedEntityTopicAnalyzer
from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.entity import ArticleEntity
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.repositories.entity_topic import EntityTopicRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class PreparedEntityTopicAnalysis:
    article_id: UUID
    expected_hash: str
    normalized_title: str
    normalized_text: str
    analysis_input: ArticleAnalysisInput


class EntityTopicAnalysisService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        analyzer: EntityTopicAnalyzer | None = None,
        repository: EntityTopicRepository | None = None,
        *,
        min_entity_confidence: float = 0.65,
        min_topic_confidence: float = 0.6,
        max_topics: int = 10,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.analyzer = analyzer or RuleBasedEntityTopicAnalyzer()
        self.repository = repository or EntityTopicRepository()
        self.entity_resolver = EntityResolver(
            self.repository,
            min_confidence=min_entity_confidence,
        )
        self.topic_resolver = TopicResolver(
            self.repository,
            min_confidence=min_topic_confidence,
        )
        self.max_topics = max_topics
        self.config_version = config_version

    def analysis_hash(
        self,
        article: Article,
    ) -> str:
        payload = [
            article.normalized_title or "",
            article.normalized_text or "",
            article.language_code or "",
            self.analyzer.provider,
            self.analyzer.version,
            self.config_version,
        ]

        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def candidate(
        self,
        article: Article,
    ) -> ArticleProcessingCandidate:
        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.analysis_hash(article),
            provider=self.analyzer.provider,
            provider_version=self.analyzer.version,
            configuration_version=self.config_version,
        )

    def prepare_analysis(
        self,
        article: Article,
    ) -> PreparedEntityTopicAnalysis:
        normalized_title = article.normalized_title or ""
        normalized_text = article.normalized_text or ""

        return PreparedEntityTopicAnalysis(
            article_id=article.id,
            expected_hash=self.analysis_hash(article),
            normalized_title=normalized_title,
            normalized_text=normalized_text,
            analysis_input=ArticleAnalysisInput(
                article.id,
                normalized_title,
                normalized_text,
                article.language_code,
                article.published_at,
                {
                    "feed_id": str(article.feed_id),
                },
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        normalized_title: str,
        normalized_text: str,
        result: AnalysisResult,
    ) -> None:
        for mention in result.entities:
            if (
                not mention.canonical_name.strip()
                or not mention.mention_text
            ):
                raise ValueError(
                    "entity names and mention text must not be empty"
                )

            if (
                not isinstance(
                    mention.entity_type,
                    EntityType,
                )
                or not isinstance(
                    mention.text_source,
                    TextPart,
                )
            ):
                raise ValueError(
                    "entity type and text source must use provider enums"
                )

            if not all(
                math.isfinite(value)
                and 0 <= value <= 1
                for value in (
                    mention.confidence,
                    mention.salience,
                )
            ):
                raise ValueError(
                    "entity confidence and salience must be between zero and one"
                )

            if (
                mention.start_offset is None
            ) != (
                mention.end_offset is None
            ):
                raise ValueError(
                    "mention offsets must both be null or both be set"
                )

            if (
                mention.sentence_index is not None
                and mention.sentence_index < 0
            ):
                raise ValueError(
                    "sentence index must not be negative"
                )

            if mention.start_offset is not None:
                assert mention.end_offset is not None

                if (
                    mention.start_offset < 0
                    or mention.end_offset
                    <= mention.start_offset
                ):
                    raise ValueError(
                        "mention offsets must define a non-empty range"
                    )

                if mention.text_source == TextPart.TITLE:
                    source_text = normalized_title
                else:
                    source_text = normalized_text

                if (
                    source_text[
                        mention.start_offset:
                        mention.end_offset
                    ]
                    != mention.mention_text
                ):
                    raise ValueError(
                        "mention offsets do not match the selected normalized field"
                    )

        for topic in result.topics:
            if not topic.name.strip():
                raise ValueError(
                    "topic name must not be empty"
                )

            if not all(
                math.isfinite(value)
                and 0 <= value <= 1
                for value in (
                    topic.relevance,
                    topic.confidence,
                )
            ):
                raise ValueError(
                    "topic relevance and confidence must be between zero and one"
                )

    def run_provider(
        self,
        prepared: PreparedEntityTopicAnalysis,
    ) -> AnalysisResult:
        result = self.analyzer.analyze(
            prepared.analysis_input
        )

        self._validate_result(
            normalized_title=prepared.normalized_title,
            normalized_text=prepared.normalized_text,
            result=result,
        )

        return result

    def persist_result(
        self,
        db: Session,
        article: Article,
        *,
        prepared: PreparedEntityTopicAnalysis,
        result: AnalysisResult,
        processing_run_id: UUID | None,
    ) -> None:
        if article.id != prepared.article_id:
            raise ValueError(
                "prepared analysis does not belong to article"
            )

        self.repository.replace_article_results(
            db,
            article.id,
        )

        seen_mentions: set[tuple] = set()

        for mention in result.entities:
            entity = self.entity_resolver.resolve(
                db,
                mention,
            )

            key = (
                entity.id if entity else None,
                mention.text_source,
                normalize_name(
                    mention.mention_text
                ),
                mention.start_offset,
                mention.end_offset,
            )

            if (
                entity is None
                or key in seen_mentions
            ):
                continue

            seen_mentions.add(key)

            db.add(
                ArticleEntity(
                    article_id=article.id,
                    entity_id=entity.id,
                    processing_run_id=processing_run_id,
                    mention_text=mention.mention_text,
                    normalized_mention=key[2],
                    entity_type=entity.entity_type,
                    text_source=mention.text_source,
                    start_offset=mention.start_offset,
                    end_offset=mention.end_offset,
                    sentence_index=mention.sentence_index,
                    confidence=mention.confidence,
                    salience=mention.salience,
                    extraction_provider=(
                        self.analyzer.provider
                    ),
                    extraction_version=(
                        self.analyzer.version
                    ),
                )
            )

        seen_topics: set[object] = set()

        for detected in sorted(
            result.topics,
            key=lambda item: (
                -item.relevance,
                item.name,
            ),
        ):
            if len(seen_topics) >= self.max_topics:
                break

            topic = self.topic_resolver.resolve(
                db,
                detected,
            )

            if (
                topic is None
                or topic.id in seen_topics
            ):
                continue

            seen_topics.add(topic.id)

            db.add(
                ArticleTopic(
                    article_id=article.id,
                    topic_id=topic.id,
                    processing_run_id=processing_run_id,
                    relevance=detected.relevance,
                    confidence=detected.confidence,
                    detection_provider=(
                        self.analyzer.provider
                    ),
                    detection_version=(
                        self.analyzer.version
                    ),
                )
            )

        db.flush()

    def analyze_article(
        self,
        db: Session,
        article: Article,
        *,
        processing_run_id: UUID | None = None,
    ) -> bool:
        prepared = self.prepare_analysis(
            article
        )

        result = self.run_provider(
            prepared
        )

        self.persist_result(
            db,
            article,
            prepared=prepared,
            result=result,
            processing_run_id=processing_run_id,
        )

        return True


class EntityTopicAnalysisRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: EntityTopicAnalysisService | None = None,
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
        self.service = (
            service
            or EntityTopicAnalysisService()
        )
        self.processing_repository = (
            processing_repository
            or ArticleProcessingRepository()
        )

        self.claim_ttl_seconds = claim_ttl_seconds
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds

        self.worker_id = (
            worker_id
            or str(uuid4())
        )
        self.clock = (
            clock
            or (
                lambda: datetime.now(UTC)
            )
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
                    .where(
                        *conditions
                    )
                    .order_by(
                        Article.created_at,
                        Article.id,
                    )
                    .limit(
                        page_size
                    )
                ).all()
            )

            if not articles:
                break

            candidates = [
                self.service.candidate(
                    article
                )
                for article in articles
            ]

            remaining = (
                limit
                - len(claims)
            )

            claims.extend(
                self.processing_repository.claim_candidates(
                    db,
                    pipeline=(
                        ArticlePipeline
                        .ENTITY_TOPIC
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
                    + timedelta(
                        seconds=delay
                    )
                ),
                error_code=(
                    type(exc).__name__
                ),
                error_message=(
                    str(exc)[:2000]
                ),
            )

        except ArticleProcessingLeaseLostError:
            self.processing_repository.mark_lease_lost(
                db,
                run_id=run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired while "
                    "handling worker failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> AnalysisBatchResult:
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
                prepared: (
                    PreparedEntityTopicAnalysis
                    | None
                ) = None

                try:
                    with db.begin():
                        article = db.scalar(
                            select(
                                Article
                            )
                            .join(Feed)
                            .join(Source)
                            .where(
                                Article.id
                                == claim.article_id,
                                Article.deleted_at
                                .is_(None),
                                Article.normalized_at
                                .is_not(None),
                                Article.normalized_text
                                .is_not(None),
                                Feed.deleted_at
                                .is_(None),
                                Feed.active
                                .is_(True),
                                Source.deleted_at
                                .is_(None),
                                Source.active
                                .is_(True),
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
                                    "after entity/topic claim"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = (
                            self.service
                            .prepare_analysis(
                                article
                            )
                        )

                    assert prepared is not None

                    try:
                        result = (
                            self.service
                            .run_provider(
                                prepared
                            )
                        )

                    except Exception as exc:
                        failure_time = (
                            self.clock()
                        )

                        with db.begin():
                            self._record_failure(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                attempt_number=(
                                    claim.attempt_number
                                ),
                                failure_time=(
                                    failure_time
                                ),
                                exc=exc,
                            )

                        failed += 1

                        logger.exception(
                            "Entity/topic article analysis failed",
                            extra={
                                "article_id": (
                                    str(
                                        claim.article_id
                                    )
                                ),
                                "provider": (
                                    self.service
                                    .analyzer
                                    .provider
                                ),
                                "version": (
                                    self.service
                                    .analyzer
                                    .version
                                ),
                                "processing_run_id": (
                                    str(
                                        claim.run_id
                                    )
                                ),
                            },
                        )

                        continue

                    try:
                        with db.begin():
                            finalization_time = (
                                self.clock()
                            )

                            lease_extended_to = (
                                finalization_time
                                + timedelta(
                                    seconds=(
                                        self.claim_ttl_seconds
                                    )
                                )
                            )

                            lease_valid = (
                                self.processing_repository
                                .heartbeat(
                                    db,
                                    state_id=claim.state_id,
                                    run_id=claim.run_id,
                                    worker_id=(
                                        self.worker_id
                                    ),
                                    now=(
                                        finalization_time
                                    ),
                                    claim_expires_at=(
                                        lease_extended_to
                                    ),
                                )
                            )

                            if not lease_valid:
                                raise ArticleProcessingLeaseLostError(
                                    "processing lease is no longer valid"
                                )

                            article = db.scalar(
                                select(
                                    Article
                                )
                                .join(Feed)
                                .join(Source)
                                .where(
                                    Article.id
                                    == claim.article_id,
                                    Article.deleted_at
                                    .is_(None),
                                    Article.normalized_at
                                    .is_not(None),
                                    Article.normalized_text
                                    .is_not(None),
                                    Feed.deleted_at
                                    .is_(None),
                                    Feed.active
                                    .is_(True),
                                    Source.deleted_at
                                    .is_(None),
                                    Source.active
                                    .is_(True),
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
                                        "before entity/topic persistence"
                                    ),
                                )
                                skipped += 1
                                continue

                            self.service.persist_result(
                                db,
                                article,
                                prepared=prepared,
                                result=result,
                                processing_run_id=(
                                    claim.run_id
                                ),
                            )

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

                        failure_time = (
                            self.clock()
                        )

                        with db.begin():
                            self._record_failure(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                attempt_number=(
                                    claim.attempt_number
                                ),
                                failure_time=(
                                    failure_time
                                ),
                                exc=exc,
                            )

                        failed += 1

                        logger.exception(
                            "Entity/topic result persistence failed",
                            extra={
                                "article_id": (
                                    str(
                                        claim.article_id
                                    )
                                ),
                                "provider": (
                                    self.service
                                    .analyzer
                                    .provider
                                ),
                                "version": (
                                    self.service
                                    .analyzer
                                    .version
                                ),
                                "processing_run_id": (
                                    str(
                                        claim.run_id
                                    )
                                ),
                            },
                        )

                except ArticleProcessingLeaseLostError:
                    skipped += 1

        return AnalysisBatchResult(
            selected=len(claims),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )