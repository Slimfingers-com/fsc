import hashlib
import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.enums.article_pipeline import ArticlePipeline
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun
from app.models.claim import ArticleClaim
from app.models.entity import ArticleEntity
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.perspectives.provider import (
    PerspectiveAnalysisInput,
    PerspectiveAnalysisResult,
    PerspectiveAnalyzer,
    PerspectiveAttribution,
    PerspectiveClaimInput,
    PerspectiveEntityMentionInput,
    PerspectiveKind,
)
from app.perspectives.rule_based import (
    RuleBasedPerspectiveAnalyzer,
)
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingClaim,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from app.repositories.perspective import (
    PerspectiveRepository,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PerspectiveAnalysisBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class PreparedPerspectiveAnalysis:
    article_id: UUID
    expected_hash: str
    title: str
    normalized_text: str
    analysis_input: PerspectiveAnalysisInput


class PerspectiveAnalysisService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        analyzer: PerspectiveAnalyzer | None = None,
        repository: PerspectiveRepository | None = None,
        *,
        min_confidence: float = 0.6,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError(
                "min_confidence must be between zero and one"
            )

        self.analyzer = (
            analyzer
            or RuleBasedPerspectiveAnalyzer()
        )
        self.repository = (
            repository
            or PerspectiveRepository()
        )
        self.min_confidence = (
            min_confidence
        )
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

    @staticmethod
    def _field_text(
        article: Article,
        text_source,
    ) -> str:
        if text_source.value == "title":
            return (
                article.normalized_title
                or ""
            )
        return (
            article.normalized_text
            or ""
        )

    def inputs_are_current(
        self,
        article: Article,
        claims: list[ArticleClaim],
        mentions: list[ArticleEntity],
    ) -> bool:
        if not claims:
            return False

        for claim in claims:
            if claim.article_id != article.id:
                return False

            field_text = self._field_text(
                article,
                claim.text_source,
            )

            if (
                claim.start_offset < 0
                or claim.end_offset
                <= claim.start_offset
                or claim.end_offset
                > len(field_text)
                or field_text[
                    claim.start_offset:
                    claim.end_offset
                ]
                != claim.claim_text
            ):
                return False

        for mention in mentions:
            if mention.article_id != article.id:
                return False

            if (
                mention.start_offset is None
            ) != (
                mention.end_offset is None
            ):
                return False

            if mention.start_offset is None:
                continue

            assert (
                mention.end_offset
                is not None
            )

            field_text = self._field_text(
                article,
                mention.text_source,
            )

            if (
                mention.start_offset < 0
                or mention.end_offset
                <= mention.start_offset
                or mention.end_offset
                > len(field_text)
                or field_text[
                    mention.start_offset:
                    mention.end_offset
                ]
                != mention.mention_text
            ):
                return False

        return True

    def analysis_hash(
        self,
        article: Article,
        claims: list[ArticleClaim],
        mentions: list[ArticleEntity],
    ) -> str:
        claim_identity = [
            [
                str(claim.id),
                str(
                    claim.processing_run_id
                ),
                claim.claim_hash,
                claim.text_source.value,
                claim.start_offset,
                claim.end_offset,
                claim.sentence_index,
                claim.confidence,
                claim.extraction_provider,
                claim.extraction_version,
            ]
            for claim in sorted(
                claims,
                key=lambda item: (
                    item.text_source.value,
                    item.sentence_index,
                    item.start_offset,
                    str(item.id),
                ),
            )
        ]

        mention_identity = [
            [
                str(mention.id),
                (
                    str(
                        mention.processing_run_id
                    )
                    if mention.processing_run_id
                    is not None
                    else None
                ),
                str(mention.entity_id),
                mention.mention_text,
                mention.normalized_mention,
                mention.entity_type.value,
                mention.text_source.value,
                mention.start_offset,
                mention.end_offset,
                mention.sentence_index,
                mention.confidence,
                mention.salience,
                mention.extraction_provider,
                mention.extraction_version,
            ]
            for mention in sorted(
                mentions,
                key=lambda item: (
                    item.text_source.value,
                    (
                        item.sentence_index
                        if item.sentence_index
                        is not None
                        else -1
                    ),
                    (
                        item.start_offset
                        if item.start_offset
                        is not None
                        else -1
                    ),
                    str(item.id),
                ),
            )
        ]

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
            claim_identity,
            mention_identity,
            self.analyzer.provider,
            self.analyzer.version,
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
        *,
        claims: list[ArticleClaim],
        mentions: list[ArticleEntity],
    ) -> ArticleProcessingCandidate:
        if not self.inputs_are_current(
            article,
            claims,
            mentions,
        ):
            raise ValueError(
                "perspective inputs are not current"
            )

        return ArticleProcessingCandidate(
            article_id=article.id,
            input_hash=self.analysis_hash(
                article,
                claims,
                mentions,
            ),
            provider=(
                self.analyzer.provider
            ),
            provider_version=(
                self.analyzer.version
            ),
            configuration_version=(
                self.processing_configuration_version
            ),
        )

    def prepare(
        self,
        article: Article,
        *,
        claims: list[ArticleClaim],
        mentions: list[ArticleEntity],
    ) -> PreparedPerspectiveAnalysis:
        candidate = self.candidate(
            article,
            claims=claims,
            mentions=mentions,
        )

        claim_inputs = tuple(
            PerspectiveClaimInput(
                claim_id=claim.id,
                claim_text=claim.claim_text,
                claim_hash=claim.claim_hash,
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
            )
            for claim in sorted(
                claims,
                key=lambda item: (
                    item.text_source.value,
                    item.sentence_index,
                    item.start_offset,
                    str(item.id),
                ),
            )
        )

        mention_inputs = tuple(
            PerspectiveEntityMentionInput(
                mention_id=mention.id,
                entity_id=mention.entity_id,
                mention_text=(
                    mention.mention_text
                ),
                entity_type=(
                    mention.entity_type
                ),
                text_source=(
                    mention.text_source
                ),
                start_offset=(
                    mention.start_offset
                ),
                end_offset=(
                    mention.end_offset
                ),
                sentence_index=(
                    mention.sentence_index
                ),
                confidence=(
                    mention.confidence
                ),
                salience=(
                    mention.salience
                ),
            )
            for mention in sorted(
                mentions,
                key=lambda item: (
                    item.text_source.value,
                    (
                        item.sentence_index
                        if item.sentence_index
                        is not None
                        else -1
                    ),
                    (
                        item.start_offset
                        if item.start_offset
                        is not None
                        else -1
                    ),
                    str(item.id),
                ),
            )
        )

        title = (
            article.normalized_title
            or ""
        )
        normalized_text = (
            article.normalized_text
            or ""
        )

        return PreparedPerspectiveAnalysis(
            article_id=article.id,
            expected_hash=(
                candidate.input_hash
            ),
            title=title,
            normalized_text=(
                normalized_text
            ),
            analysis_input=(
                PerspectiveAnalysisInput(
                    article_id=(
                        article.id
                    ),
                    title=title,
                    normalized_text=(
                        normalized_text
                    ),
                    language_code=(
                        article.language_code
                    ),
                    claims=claim_inputs,
                    entity_mentions=(
                        mention_inputs
                    ),
                )
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedPerspectiveAnalysis,
        result: PerspectiveAnalysisResult,
    ) -> None:
        claims = {
            claim.claim_id: claim
            for claim
            in prepared.analysis_input.claims
        }
        mentions = {
            mention.mention_id: mention
            for mention
            in prepared.analysis_input.entity_mentions
        }

        seen: set[
            tuple[
                UUID,
                UUID | None,
                PerspectiveKind,
            ]
        ] = set()
        covered_claim_ids: set[
            UUID
        ] = set()

        for attribution in result.attributions:
            if not isinstance(
                attribution.perspective_kind,
                PerspectiveKind,
            ):
                raise ValueError(
                    "perspective kind must use PerspectiveKind"
                )

            claim = claims.get(
                attribution.claim_id
            )

            if claim is None:
                raise ValueError(
                    "perspective references an unknown claim"
                )

            holder = None

            if (
                attribution.perspective_kind
                == PerspectiveKind.UNATTRIBUTED
            ):
                if (
                    attribution.holder_mention_id
                    is not None
                ):
                    raise ValueError(
                        "unattributed perspective must not reference a holder"
                    )
            else:
                if (
                    attribution.holder_mention_id
                    is None
                ):
                    raise ValueError(
                        "attributed perspective must reference a holder mention"
                    )

                holder = mentions.get(
                    attribution.holder_mention_id
                )

                if holder is None:
                    raise ValueError(
                        "perspective references an unknown holder mention"
                    )

            if not (
                math.isfinite(
                    attribution.confidence
                )
                and 0
                <= attribution.confidence
                <= 1
            ):
                raise ValueError(
                    "perspective confidence must be between zero and one"
                )

            if (
                attribution.start_offset
                < 0
                or attribution.end_offset
                <= attribution.start_offset
                or attribution.sentence_index
                < 0
            ):
                raise ValueError(
                    "perspective evidence span is invalid"
                )

            if (
                attribution.text_source
                != claim.text_source
            ):
                raise ValueError(
                    "perspective evidence must use the claim text source"
                )

            field_text = (
                prepared.title
                if attribution.text_source.value
                == "title"
                else prepared.normalized_text
            )

            if (
                attribution.end_offset
                > len(field_text)
                or field_text[
                    attribution.start_offset:
                    attribution.end_offset
                ]
                != attribution.evidence_text
            ):
                raise ValueError(
                    "perspective evidence offsets do not match the normalized field"
                )

            if not (
                attribution.start_offset
                <= claim.start_offset
                and claim.end_offset
                <= attribution.end_offset
            ):
                raise ValueError(
                    "perspective evidence must contain the claim span"
                )

            if holder is not None:
                if (
                    holder.start_offset
                    is None
                    or holder.end_offset
                    is None
                ):
                    raise ValueError(
                        "holder mention must have exact offsets"
                    )

                if (
                    holder.text_source
                    != attribution.text_source
                    or not (
                        attribution.start_offset
                        <= holder.start_offset
                        and holder.end_offset
                        <= attribution.end_offset
                    )
                ):
                    raise ValueError(
                        "holder mention must be contained in perspective evidence"
                    )

            key = (
                attribution.claim_id,
                attribution.holder_mention_id,
                attribution.perspective_kind,
            )

            if key in seen:
                raise ValueError(
                    "duplicate perspective attribution"
                )

            seen.add(key)
            covered_claim_ids.add(
                attribution.claim_id
            )

        attributions_by_claim: dict[
            UUID,
            list[PerspectiveAttribution],
        ] = {}

        for attribution in result.attributions:
            attributions_by_claim.setdefault(
                attribution.claim_id,
                [],
            ).append(
                attribution
            )

        for claim_attributions in attributions_by_claim.values():
            if (
                len(claim_attributions) > 1
                and any(
                    item.perspective_kind
                    == PerspectiveKind.UNATTRIBUTED
                    for item
                    in claim_attributions
                )
            ):
                raise ValueError(
                    "unattributed perspective cannot coexist with attributed perspectives"
                )

        if (
            covered_claim_ids
            != set(claims)
        ):
            raise ValueError(
                "perspective result must classify every claim"
            )

    def run_provider(
        self,
        prepared: PreparedPerspectiveAnalysis,
    ) -> PerspectiveAnalysisResult:
        result = self.analyzer.analyze(
            prepared.analysis_input
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
        claims: list[ArticleClaim],
        mentions: list[ArticleEntity],
        prepared: PreparedPerspectiveAnalysis,
        result: PerspectiveAnalysisResult,
        processing_run_id: UUID,
        analyzed_at: datetime,
    ) -> None:
        if (
            article.id
            != prepared.article_id
        ):
            raise ValueError(
                "prepared perspective analysis does not belong to article"
            )

        if not self.inputs_are_current(
            article,
            claims,
            mentions,
        ):
            raise ValueError(
                "perspective inputs changed after analysis was prepared"
            )

        current_hash = self.analysis_hash(
            article,
            claims,
            mentions,
        )

        if (
            current_hash
            != prepared.expected_hash
        ):
            raise ValueError(
                "perspective input identity changed after analysis was prepared"
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
            .PERSPECTIVE_ANALYSIS
            .value
            or run.input_hash
            != prepared.expected_hash
            or run.provider
            != self.analyzer.provider
            or run.provider_version
            != self.analyzer.version
            or run.configuration_version
            != self.processing_configuration_version
        ):
            raise ValueError(
                "processing run does not match perspective analysis identity"
            )

        self._validate_result(
            prepared=prepared,
            result=result,
        )

        claim_by_id = {
            claim.id: claim
            for claim in claims
        }
        mention_by_id = {
            mention.id: mention
            for mention in mentions
        }

        selected: dict[
            tuple[
                UUID,
                UUID | None,
                PerspectiveKind,
            ],
            tuple[
                PerspectiveAttribution,
                ArticleEntity | None,
            ],
        ] = {}

        for attribution in result.attributions:
            if (
                attribution.confidence
                < self.min_confidence
            ):
                continue

            holder = (
                mention_by_id.get(
                    attribution.holder_mention_id
                )
                if attribution.holder_mention_id
                is not None
                else None
            )
            holder_entity_id = (
                holder.entity_id
                if holder is not None
                else None
            )

            key = (
                attribution.claim_id,
                holder_entity_id,
                attribution.perspective_kind,
            )

            previous = selected.get(key)

            if (
                previous is None
                or attribution.confidence
                > previous[0].confidence
                or (
                    attribution.confidence
                    == previous[0].confidence
                    and (
                        attribution.start_offset,
                        attribution.end_offset,
                        str(
                            attribution.holder_mention_id
                            or ""
                        ),
                    )
                    < (
                        previous[0].start_offset,
                        previous[0].end_offset,
                        str(
                            previous[0].holder_mention_id
                            or ""
                        ),
                    )
                )
            ):
                selected[key] = (
                    attribution,
                    holder,
                )

        self.repository.replace_article_results(
            db,
            article_id=article.id,
            now=analyzed_at,
        )

        ordered = sorted(
            selected.values(),
            key=lambda item: (
                (
                    claim_by_id[
                        item[0].claim_id
                    ].text_source.value
                ),
                claim_by_id[
                    item[0].claim_id
                ].sentence_index,
                claim_by_id[
                    item[0].claim_id
                ].start_offset,
                item[0].perspective_kind.value,
                (
                    str(
                        item[1].entity_id
                    )
                    if item[1]
                    is not None
                    else ""
                ),
            ),
        )

        for attribution, holder in ordered:
            db.add(
                ArticlePerspective(
                    article_id=(
                        article.id
                    ),
                    claim_id=(
                        attribution.claim_id
                    ),
                    processing_run_id=(
                        processing_run_id
                    ),
                    holder_entity_id=(
                        holder.entity_id
                        if holder
                        is not None
                        else None
                    ),
                    holder_text=(
                        holder.mention_text
                        if holder
                        is not None
                        else None
                    ),
                    holder_start_offset=(
                        holder.start_offset
                        if holder
                        is not None
                        else None
                    ),
                    holder_end_offset=(
                        holder.end_offset
                        if holder
                        is not None
                        else None
                    ),
                    perspective_kind=(
                        attribution.perspective_kind
                    ),
                    evidence_text=(
                        attribution.evidence_text
                    ),
                    text_source=(
                        attribution.text_source
                    ),
                    start_offset=(
                        attribution.start_offset
                    ),
                    end_offset=(
                        attribution.end_offset
                    ),
                    sentence_index=(
                        attribution.sentence_index
                    ),
                    confidence=(
                        attribution.confidence
                    ),
                    analysis_provider=(
                        self.analyzer.provider
                    ),
                    analysis_version=(
                        self.analyzer.version
                    ),
                    analyzed_at=(
                        analyzed_at
                    ),
                )
            )

        db.flush()


class PerspectiveAnalysisRunner:
    def __init__(
        self,
        session_factory: sessionmaker[
            Session
        ],
        service: PerspectiveAnalysisService
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
                "perspective claim and retry timing settings are invalid"
            )

        self.session_factory = (
            session_factory
        )
        self.service = (
            service
            or PerspectiveAnalysisService()
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
                .execution_options(
                    populate_existing=True
                )
            )

        return db.scalar(
            statement
        )

    def _load_inputs(
        self,
        db: Session,
        *,
        article_id: UUID,
        for_update: bool = False,
    ) -> tuple[
        list[ArticleClaim],
        list[ArticleEntity],
    ]:
        claims = (
            self.service.repository
            .load_active_claims(
                db,
                article_ids=[
                    article_id
                ],
                for_update=for_update,
            )
            .get(
                article_id,
                [],
            )
        )
        mentions = (
            self.service.repository
            .load_active_mentions(
                db,
                article_ids=[
                    article_id
                ],
                for_update=for_update,
            )
            .get(
                article_id,
                [],
            )
        )
        return claims, mentions

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

        while len(claims) < limit:
            conditions = list(
                self._eligibility_conditions()
            )
            conditions.append(
                exists(
                    select(
                        ArticleClaim.id
                    ).where(
                        ArticleClaim.article_id
                        == Article.id,
                        ArticleClaim.deleted_at.is_(
                            None
                        ),
                    )
                )
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

            article_ids = [
                article.id
                for article in articles
            ]
            claims_by_article = (
                self.service.repository
                .load_active_claims(
                    db,
                    article_ids=article_ids,
                )
            )
            mentions_by_article = (
                self.service.repository
                .load_active_mentions(
                    db,
                    article_ids=article_ids,
                )
            )

            candidates: list[
                ArticleProcessingCandidate
            ] = []

            for article in articles:
                article_claims = (
                    claims_by_article.get(
                        article.id,
                        [],
                    )
                )
                article_mentions = (
                    mentions_by_article.get(
                        article.id,
                        [],
                    )
                )

                if not self.service.inputs_are_current(
                    article,
                    article_claims,
                    article_mentions,
                ):
                    continue

                candidates.append(
                    self.service.candidate(
                        article,
                        claims=article_claims,
                        mentions=article_mentions,
                    )
                )

            if candidates:
                claims.extend(
                    self.processing_repository.claim_candidates(
                        db,
                        pipeline=(
                            ArticlePipeline
                            .PERSPECTIVE_ANALYSIS
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
                    "processing lease expired while handling perspective failure"
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
    ) -> PerspectiveAnalysisBatchResult:
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
                invalidated_article_ids = (
                    self.service.repository
                    .deactivate_for_inactive_claims(
                        db,
                        now=claim_now,
                    )
                )

                if invalidated_article_ids:
                    self.processing_repository.invalidate_processed(
                        db,
                        pipeline=(
                            ArticlePipeline
                            .PERSPECTIVE_ANALYSIS
                            .value
                        ),
                        article_ids=(
                            invalidated_article_ids
                        ),
                    )

            with db.begin():
                claimed = self._claim_pending(
                    db,
                    limit=limit,
                    now=claim_now,
                )

            for claim in claimed:
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

                        (
                            current_claims,
                            current_mentions,
                        ) = self._load_inputs(
                            db,
                            article_id=(
                                article.id
                            ),
                        )

                        if not self.service.inputs_are_current(
                            article,
                            current_claims,
                            current_mentions,
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
                                    "perspective inputs are no longer current"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                article,
                                claims=(
                                    current_claims
                                ),
                                mentions=(
                                    current_mentions
                                ),
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
                                    "perspective input identity changed before provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = (
                            self.service.prepare(
                                article,
                                claims=(
                                    current_claims
                                ),
                                mentions=(
                                    current_mentions
                                ),
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
                                "processing lease was lost before perspective provider execution"
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
                        "Perspective analysis failed",
                        extra={
                            "article_id": str(
                                claim.article_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                            "provider": (
                                self.service
                                .analyzer
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
                                    "processing lease was lost before perspective finalization"
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
                                    "article became ineligible during perspective analysis"
                                ),
                            )
                            skipped += 1
                            continue

                        (
                            final_claims,
                            final_mentions,
                        ) = self._load_inputs(
                            db,
                            article_id=(
                                article.id
                            ),
                            for_update=True,
                        )

                        if not self.service.inputs_are_current(
                            article,
                            final_claims,
                            final_mentions,
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
                                    "perspective inputs became stale during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                article,
                                claims=(
                                    final_claims
                                ),
                                mentions=(
                                    final_mentions
                                ),
                            )
                        )

                        if (
                            not claim.matches_candidate(
                                current
                            )
                            or current.input_hash
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
                                    "perspective input identity changed during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        self.service.persist_result(
                            db,
                            article,
                            claims=(
                                final_claims
                            ),
                            mentions=(
                                final_mentions
                            ),
                            prepared=(
                                prepared
                            ),
                            result=result,
                            processing_run_id=(
                                claim.run_id
                            ),
                            analyzed_at=(
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
                                "processing lease was lost during perspective finalization"
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
                        "Perspective analysis finalization failed",
                        extra={
                            "article_id": str(
                                claim.article_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                        },
                    )

        return PerspectiveAnalysisBatchResult(
            selected=len(claimed),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
