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

from app.analysis.provider import TextPart
from app.claims.provider import (
    ClaimExtractionInput,
    ClaimExtractionResult,
    ClaimExtractor,
    normalize_claim_text,
)
from app.claims.rule_based import (
    RuleBasedClaimExtractor,
)
from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.repositories.claim import ClaimRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClaimExtractionBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class PreparedClaimExtraction:
    article_id: UUID
    expected_hash: str
    title: str
    normalized_text: str
    extraction_input: ClaimExtractionInput


class ClaimExtractionService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        extractor: ClaimExtractor | None = None,
        repository: ClaimRepository | None = None,
        *,
        min_confidence: float = 0.6,
        max_claims: int = 30,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        if not (
            0
            <= min_confidence
            <= 1
        ):
            raise ValueError(
                "min_confidence must be between zero and one"
            )

        if max_claims <= 0:
            raise ValueError(
                "max_claims must be greater than zero"
            )

        self.extractor = (
            extractor
            or RuleBasedClaimExtractor()
        )
        self.repository = (
            repository
            or ClaimRepository()
        )
        self.min_confidence = (
            min_confidence
        )
        self.max_claims = max_claims
        self.config_version = (
            config_version
        )

    @property
    def processing_configuration_version(
        self,
    ) -> str:
        payload = {
            "base_version": (
                self.config_version
            ),
            "min_confidence": (
                self.min_confidence
            ),
            "max_claims": (
                self.max_claims
            ),
        }

        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _datetime_identity(
        value: datetime | None,
    ) -> str | None:
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=UTC
            )

        return value.astimezone(
            UTC
        ).isoformat(
            timespec="microseconds"
        )

    def extraction_hash(
        self,
        article: Article,
    ) -> str:
        payload = [
            article.normalized_title
            or "",
            article.normalized_text
            or "",
            article.language_code
            or "",
            article.content_hash
            or "",
            article.normalization_version,
            self._datetime_identity(
                article.published_at
            ),
            str(article.feed_id),
            self.extractor.provider,
            self.extractor.version,
            self.processing_configuration_version,
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
        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=(
                self.extraction_hash(
                    article
                )
            ),
            provider=(
                self.extractor.provider
            ),
            provider_version=(
                self.extractor.version
            ),
            configuration_version=(
                self.processing_configuration_version
            ),
        )

    def prepare(
        self,
        article: Article,
    ) -> PreparedClaimExtraction:
        title = (
            article.normalized_title
            or ""
        )
        normalized_text = (
            article.normalized_text
            or ""
        )

        return PreparedClaimExtraction(
            article_id=article.id,
            expected_hash=(
                self.extraction_hash(
                    article
                )
            ),
            title=title,
            normalized_text=(
                normalized_text
            ),
            extraction_input=(
                ClaimExtractionInput(
                    article_id=article.id,
                    title=title,
                    normalized_text=(
                        normalized_text
                    ),
                    language_code=(
                        article.language_code
                    ),
                    published_at=(
                        article.published_at
                    ),
                    source_metadata={
                        "feed_id": str(
                            article.feed_id
                        )
                    },
                )
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedClaimExtraction,
        result: ClaimExtractionResult,
    ) -> None:
        for claim in result.claims:
            if not isinstance(
                claim.text_source,
                TextPart,
            ):
                raise ValueError(
                    "claim text_source must use TextPart"
                )

            if not claim.claim_text:
                raise ValueError(
                    "claim text must not be empty"
                )

            if not (
                math.isfinite(
                    claim.confidence
                )
                and 0
                <= claim.confidence
                <= 1
            ):
                raise ValueError(
                    "claim confidence must be between zero and one"
                )

            if (
                claim.start_offset < 0
                or claim.end_offset
                <= claim.start_offset
                or claim.sentence_index
                < 0
            ):
                raise ValueError(
                    "claim offsets and sentence index are invalid"
                )

            source_text = (
                prepared.title
                if claim.text_source.value
                == "title"
                else prepared.normalized_text
            )

            if (
                claim.end_offset
                > len(source_text)
                or source_text[
                    claim.start_offset:
                    claim.end_offset
                ]
                != claim.claim_text
            ):
                raise ValueError(
                    "claim offsets do not match the selected normalized field"
                )

            if not normalize_claim_text(
                claim.claim_text
            ):
                raise ValueError(
                    "normalized claim text must not be empty"
                )

    def run_provider(
        self,
        prepared: PreparedClaimExtraction,
    ) -> ClaimExtractionResult:
        result = self.extractor.extract(
            prepared.extraction_input
        )

        self._validate_result(
            prepared=prepared,
            result=result,
        )

        return result

    def persist_result(
        self,
        db: Session,
        article: Article,
        *,
        prepared: PreparedClaimExtraction,
        result: ClaimExtractionResult,
        processing_run_id: UUID,
        extracted_at: datetime,
    ) -> None:
        if (
            article.id
            != prepared.article_id
        ):
            raise ValueError(
                "prepared extraction does not belong to article"
            )

        if (
            self.extraction_hash(
                article
            )
            != prepared.expected_hash
        ):
            raise ValueError(
                "article identity changed after claim extraction was prepared"
            )

        run = db.get(
            ArticleProcessingRun,
            processing_run_id,
        )

        if (
            run is None
            or run.finished_at
            is not None
            or run.outcome
            is not None
            or run.article_id
            != article.id
            or run.pipeline
            != ArticlePipeline
            .CLAIM_EXTRACTION
            .value
            or run.input_hash
            != prepared.expected_hash
            or run.provider
            != self.extractor.provider
            or run.provider_version
            != self.extractor.version
            or run.configuration_version
            != self.processing_configuration_version
        ):
            raise ValueError(
                "processing run does not match claim extraction identity"
            )

        ranked = sorted(
            (
                claim
                for claim in result.claims
                if claim.confidence
                >= self.min_confidence
            ),
            key=lambda item: (
                -item.confidence,
                item.text_source.value,
                item.start_offset,
            ),
        )

        selected = []
        seen_hashes: set[str] = set()

        for claim in ranked:
            normalized = normalize_claim_text(
                claim.claim_text
            )
            claim_hash = hashlib.sha256(
                normalized.encode(
                    "utf-8"
                )
            ).hexdigest()

            if claim_hash in seen_hashes:
                continue

            seen_hashes.add(
                claim_hash
            )
            selected.append(
                (
                    claim,
                    normalized,
                    claim_hash,
                )
            )

            if (
                len(selected)
                >= self.max_claims
            ):
                break

        selected.sort(
            key=lambda item: (
                item[0].text_source.value,
                item[0].sentence_index,
                item[0].start_offset,
                item[2],
            )
        )

        self.repository.replace_article_results(
            db,
            article_id=article.id,
            now=extracted_at,
        )

        for (
            claim,
            normalized,
            claim_hash,
        ) in selected:
            db.add(
                ArticleClaim(
                    article_id=article.id,
                    processing_run_id=(
                        processing_run_id
                    ),
                    claim_text=(
                        claim.claim_text
                    ),
                    normalized_claim=(
                        normalized
                    ),
                    claim_hash=(
                        claim_hash
                    ),
                    text_source=(
                        claim.text_source
                    ),
                    start_offset=(
                        claim.start_offset
                    ),
                    end_offset=(
                        claim.end_offset
                    ),
                    sentence_index=(
                        claim.sentence_index
                    ),
                    confidence=(
                        claim.confidence
                    ),
                    extraction_provider=(
                        self.extractor.provider
                    ),
                    extraction_version=(
                        self.extractor.version
                    ),
                    extracted_at=(
                        extracted_at
                    ),
                )
            )

        db.flush()


class ClaimExtractionRunner:
    def __init__(
        self,
        session_factory: sessionmaker[
            Session
        ],
        service: ClaimExtractionService
        | None = None,
        processing_repository: (
            ArticleProcessingRepository
            | None
        ) = None,
        *,
        claim_ttl_seconds: float = 300,
        retry_base_seconds: float = 30,
        retry_max_seconds: float = 3600,
        worker_id: str | None = None,
        clock: Callable[
            [],
            datetime,
        ]
        | None = None,
    ) -> None:
        if (
            claim_ttl_seconds <= 0
            or retry_base_seconds <= 0
            or retry_max_seconds
            < retry_base_seconds
        ):
            raise ValueError(
                "claim and retry timing settings are invalid"
            )

        self.session_factory = (
            session_factory
        )
        self.service = (
            service
            or ClaimExtractionService()
        )
        self.processing_repository = (
            processing_repository
            or ArticleProcessingRepository()
        )
        self.claim_ttl_seconds = (
            claim_ttl_seconds
        )
        self.retry_base_seconds = (
            retry_base_seconds
        )
        self.retry_max_seconds = (
            retry_max_seconds
        )
        self.worker_id = (
            worker_id
            or str(uuid4())
        )
        self.clock = (
            clock
            or (
                lambda: datetime.now(
                    UTC
                )
            )
        )

    @staticmethod
    def _eligibility_conditions():
        return (
            Article.deleted_at.is_(None),
            Article.normalized_at.is_not(
                None
            ),
            Article.normalized_text.is_not(
                None
            ),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            Source.deleted_at.is_(None),
            Source.active.is_(True),
        )

    def _load_eligible_article(
        self,
        db: Session,
        *,
        article_id: UUID,
        for_update: bool = False,
    ) -> Article | None:
        statement = (
            select(Article)
            .join(
                Feed,
                Feed.id
                == Article.feed_id,
            )
            .join(
                Source,
                Source.id
                == Feed.source_id,
            )
            .where(
                Article.id
                == article_id,
                *self._eligibility_conditions(),
            )
        )

        if for_update:
            statement = (
                statement.with_for_update(
                    of=Article
                )
            )

        return db.scalar(
            statement
        )

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[
        ArticleProcessingClaim
    ]:
        claims: list[
            ArticleProcessingClaim
        ] = []
        page_size = max(
            100,
            limit * 4,
        )
        last_created_at = None
        last_article_id = None

        while (
            len(claims)
            < limit
        ):
            conditions = list(
                self._eligibility_conditions()
            )

            if (
                last_created_at
                is not None
                and last_article_id
                is not None
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
                for article
                in articles
            ]

            claims.extend(
                self.processing_repository.claim_candidates(
                    db,
                    pipeline=(
                        ArticlePipeline
                        .CLAIM_EXTRACTION
                        .value
                    ),
                    candidates=candidates,
                    worker_id=(
                        self.worker_id
                    ),
                    now=now,
                    claim_expires_at=(
                        now
                        + timedelta(
                            seconds=(
                                self.claim_ttl_seconds
                            )
                        )
                    ),
                    limit=(
                        limit
                        - len(claims)
                    ),
                )
            )

            last = articles[-1]
            last_created_at = (
                last.created_at
            )
            last_article_id = (
                last.id
            )

            if (
                len(articles)
                < page_size
            ):
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
                    claim.attempt_number
                    - 1,
                    0,
                )
            ),
        )

        try:
            self.processing_repository.fail(
                db,
                state_id=(
                    claim.state_id
                ),
                run_id=claim.run_id,
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
        except (
            ArticleProcessingLeaseLostError
        ):
            self.processing_repository.mark_lease_lost(
                db,
                run_id=claim.run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired while handling worker failure"
                ),
            )

    def _mark_lease_lost(
        self,
        db: Session,
        *,
        claim: ArticleProcessingClaim,
        now: datetime,
        message: str,
    ) -> None:
        self.processing_repository.mark_lease_lost(
            db,
            run_id=claim.run_id,
            now=now,
            error_message=message,
        )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> ClaimExtractionBatchResult:
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
                prepared = None

                try:
                    with db.begin():
                        article = (
                            self._load_eligible_article(
                                db,
                                article_id=(
                                    claim.article_id
                                ),
                            )
                        )
                        now = self.clock()

                        if article is None:
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=now,
                                reason=(
                                    "article is no longer eligible"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                article
                            )
                        )

                        if not claim.matches_candidate(
                            current
                        ):
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=now,
                                reason=(
                                    "article identity changed before provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = (
                            self.service.prepare(
                                article
                            )
                        )

                except (
                    ArticleProcessingLeaseLostError
                ):
                    with db.begin():
                        self._mark_lease_lost(
                            db,
                            claim=claim,
                            now=self.clock(),
                            message=(
                                "processing lease was lost before provider execution"
                            ),
                        )
                    skipped += 1
                    continue

                assert (
                    prepared
                    is not None
                )

                try:
                    result = (
                        self.service.run_provider(
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
                            claim=claim,
                            failure_time=(
                                failure_time
                            ),
                            exc=exc,
                        )

                    failed += 1

                    logger.exception(
                        "Claim extraction failed",
                        extra={
                            "article_id": str(
                                claim.article_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                            "provider": (
                                self.service
                                .extractor
                                .provider
                            ),
                        },
                    )
                    continue

                try:
                    with db.begin():
                        finalization_time = (
                            self.clock()
                        )

                        heartbeat_ok = (
                            self.processing_repository.heartbeat(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=(
                                    finalization_time
                                ),
                                claim_expires_at=(
                                    finalization_time
                                    + timedelta(
                                        seconds=(
                                            self.claim_ttl_seconds
                                        )
                                    )
                                ),
                            )
                        )

                        if not heartbeat_ok:
                            self._mark_lease_lost(
                                db,
                                claim=claim,
                                now=(
                                    finalization_time
                                ),
                                message=(
                                    "processing lease was lost before finalization"
                                ),
                            )
                            skipped += 1
                            continue

                        article = (
                            self._load_eligible_article(
                                db,
                                article_id=(
                                    claim.article_id
                                ),
                                for_update=True,
                            )
                        )

                        if article is None:
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=(
                                    finalization_time
                                ),
                                reason=(
                                    "article became ineligible during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                article
                            )
                        )

                        if (
                            not claim.matches_candidate(
                                current
                            )
                            or self.service.extraction_hash(
                                article
                            )
                            != prepared.expected_hash
                        ):
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=(
                                    finalization_time
                                ),
                                reason=(
                                    "article identity changed during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        self.service.persist_result(
                            db,
                            article,
                            prepared=(
                                prepared
                            ),
                            result=result,
                            processing_run_id=(
                                claim.run_id
                            ),
                            extracted_at=(
                                finalization_time
                            ),
                        )

                        self.processing_repository.complete(
                            db,
                            state_id=(
                                claim.state_id
                            ),
                            run_id=(
                                claim.run_id
                            ),
                            worker_id=(
                                self.worker_id
                            ),
                            now=(
                                finalization_time
                            ),
                        )

                    processed += 1

                except (
                    ArticleProcessingLeaseLostError
                ):
                    with db.begin():
                        self._mark_lease_lost(
                            db,
                            claim=claim,
                            now=self.clock(),
                            message=(
                                "processing lease was lost during finalization"
                            ),
                        )

                    skipped += 1

                except Exception as exc:
                    failure_time = (
                        self.clock()
                    )

                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=(
                                failure_time
                            ),
                            exc=exc,
                        )

                    failed += 1

                    logger.exception(
                        "Claim extraction finalization failed",
                        extra={
                            "article_id": str(
                                claim.article_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                        },
                    )

        return ClaimExtractionBatchResult(
            selected=len(claims),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
