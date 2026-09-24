import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.consensus.rule_based import RuleBasedConsensusAnalyzer
from app.coverage.provider import (
    CoverageAnalyzer,
    CoverageDifferenceInput,
    CoverageGapKind,
    CoverageGroupInput,
    CoverageSourceInput,
    MissingPerspectiveKind,
    StoryCoverageInput,
    StoryCoverageResult,
)
from app.coverage.rule_based import RuleBasedCoverageAnalyzer
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.consensus import (
    StoryConsensusSummary,
    StoryDifferenceSummary,
)
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.story_processing import StoryProcessingRun
from app.repositories.coverage import (
    CoverageRepository,
    CoverageSourceRow,
)
from app.repositories.story import StoryRepository
from app.repositories.story_processing import (
    StoryProcessingCandidate,
    StoryProcessingClaim,
    StoryProcessingLeaseLostError,
    StoryProcessingRepository,
)
from app.services.consensus import (
    ConsensusService,
    ConsensusSnapshot,
)
from app.services.source_independence import SourceIndependenceResolver


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CoverageBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class CoverageMetrics:
    article_count: int
    source_count: int
    content_source_count: int
    signal_source_count: int
    independent_content_source_count: int
    claim_group_count: int
    shared_group_count: int
    difference_count: int
    attributed_group_count: int
    source_type_counts: dict[str, int]
    coverage_scope_counts: dict[str, int]
    country_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class CoverageSnapshot:
    consensus_snapshot: ConsensusSnapshot
    source_rows: tuple[CoverageSourceRow, ...]
    consensus_summaries: tuple[
        StoryConsensusSummary,
        ...
    ]
    difference_summaries: tuple[
        StoryDifferenceSummary,
        ...
    ]
    consensus_processing_run_id: UUID


@dataclass(frozen=True, slots=True)
class PreparedCoverageAnalysis:
    story_id: UUID
    language_code: str | None
    expected_hash: str
    analysis_input: StoryCoverageInput
    metrics: CoverageMetrics


class CoverageService:
    CONFIG_VERSION = "3"

    def __init__(
        self,
        analyzer: CoverageAnalyzer | None = None,
        repository: CoverageRepository | None = None,
        consensus_service: ConsensusService | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.analyzer = analyzer or RuleBasedCoverageAnalyzer()
        self.repository = repository or CoverageRepository()
        self.consensus_service = (
            consensus_service
            or ConsensusService(
                analyzer=RuleBasedConsensusAnalyzer()
            )
        )
        self.config_version = config_version
        if not config_version:
            raise ValueError("config_version must not be empty")

    @property
    def processing_configuration_version(self) -> str:
        payload = {
            "base_version": self.config_version,
            "analyzer_configuration": self.analyzer.configuration(),
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _enum_value(value) -> str:
        return (
            value.value
            if hasattr(value, "value")
            else str(value)
        )

    @staticmethod
    def _independence_resolver(
        snapshot: CoverageSnapshot,
    ) -> SourceIndependenceResolver:
        consensus_snapshot = snapshot.consensus_snapshot
        return SourceIndependenceResolver(
            relations=consensus_snapshot.source_relations,
            provenance=consensus_snapshot.article_provenance,
        )

    @staticmethod
    def _article_independence_keys(
        snapshot: CoverageSnapshot,
        resolver: SourceIndependenceResolver,
    ) -> dict[UUID, str]:
        articles = {
            row.article.id: (
                row.article.id,
                row.source.id,
                row.membership.article_time,
            )
            for row in snapshot.source_rows
        }
        return resolver.article_component_keys(
            articles=tuple(
                articles[article_id]
                for article_id in sorted(articles, key=str)
            )
        )

    def load_snapshot(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
        lock_articles: bool = False,
    ) -> CoverageSnapshot | None:
        consensus_snapshot = (
            self.consensus_service.load_snapshot(
                db,
                story_id=story_id,
                for_update=for_update,
                lock_articles=lock_articles,
            )
        )
        if consensus_snapshot is None:
            return None

        source_rows = self.repository.load_source_rows(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if not source_rows:
            return None

        membership_ids = {
            item.membership.id
            for item in consensus_snapshot.memberships
        }
        if {
            item.membership.id
            for item in source_rows
        } != membership_ids:
            return None

        consensus_summaries = (
            self.repository.load_consensus_summaries(
                db,
                story_id=story_id,
                for_update=for_update,
            )
        )
        if not consensus_summaries:
            return None

        active_group_ids = {
            row.group.id
            for row in consensus_snapshot.rows
        }
        if {
            item.claim_group_id
            for item in consensus_summaries
        } != active_group_ids:
            return None

        difference_summaries = (
            self.repository.load_difference_summaries(
                db,
                story_id=story_id,
                for_update=for_update,
            )
        )
        active_relation_ids = {
            item.id
            for item in consensus_snapshot.relations
        }
        if {
            item.claim_relation_id
            for item in difference_summaries
        } != active_relation_ids:
            return None

        processing_run_ids = {
            item.processing_run_id
            for item in consensus_summaries
        } | {
            item.processing_run_id
            for item in difference_summaries
        }
        if len(processing_run_ids) != 1:
            return None

        processing_run_id = next(
            iter(processing_run_ids)
        )
        run = db.get(
            StoryProcessingRun,
            processing_run_id,
        )
        current_consensus_hash = (
            self.consensus_service.analysis_hash(
                consensus_snapshot
            )
        )
        if (
            run is None
            or run.story_id != story_id
            or run.pipeline
            != StoryPipeline.CONSENSUS_ANALYSIS.value
            or run.outcome != "succeeded"
            or run.finished_at is None
            or run.input_hash != current_consensus_hash
            or run.provider
            != self.consensus_service.analyzer.provider
            or run.provider_version
            != self.consensus_service.analyzer.version
            or run.configuration_version
            != self.consensus_service
            .processing_configuration_version
        ):
            return None

        return CoverageSnapshot(
            consensus_snapshot=consensus_snapshot,
            source_rows=tuple(source_rows),
            consensus_summaries=tuple(
                consensus_summaries
            ),
            difference_summaries=tuple(
                difference_summaries
            ),
            consensus_processing_run_id=(
                processing_run_id
            ),
        )

    def analysis_hash(
        self,
        snapshot: CoverageSnapshot,
    ) -> str:
        independence = self._independence_resolver(snapshot)
        article_independence_keys = self._article_independence_keys(
            snapshot,
            independence,
        )
        source_identity = [
            [
                str(row.membership.id),
                str(row.membership.processing_run_id),
                str(row.article.id),
                str(row.source.id),
                self._enum_value(
                    row.source.source_type
                ),
                (
                    self._enum_value(
                        row.source.coverage_scope
                    )
                    if row.source.coverage_scope
                    is not None
                    else ""
                ),
                row.source.country or "",
                article_independence_keys[row.article.id],
            ]
            for row in snapshot.source_rows
        ]
        consensus_identity = [
            [
                str(item.id),
                str(item.processing_run_id),
                str(item.claim_group_id),
                self._enum_value(
                    item.consensus_kind
                ),
                item.claim_count,
                item.article_count,
                item.independent_source_count,
                item.evidence_item_count,
                item.evidence_source_count,
                item.attributed_perspective_count,
            ]
            for item in snapshot.consensus_summaries
        ]
        difference_identity = [
            [
                str(item.id),
                str(item.processing_run_id),
                str(item.claim_relation_id),
                str(item.left_group_id),
                str(item.right_group_id),
                self._enum_value(
                    item.difference_kind
                ),
                item.left_independent_source_count,
                item.right_independent_source_count,
                item.left_evidence_source_count,
                item.right_evidence_source_count,
            ]
            for item in snapshot.difference_summaries
        ]
        payload = [
            str(
                snapshot.consensus_snapshot.story.id
            ),
            (
                snapshot.consensus_snapshot
                .story.language_code
                or ""
            ),
            str(
                snapshot.consensus_processing_run_id
            ),
            source_identity,
            consensus_identity,
            difference_identity,
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
        snapshot: CoverageSnapshot,
    ) -> StoryProcessingCandidate:
        return StoryProcessingCandidate(
            story_id=(
                snapshot.consensus_snapshot.story.id
            ),
            input_hash=self.analysis_hash(
                snapshot
            ),
            provider=self.analyzer.provider,
            provider_version=self.analyzer.version,
            configuration_version=(
                self
                .processing_configuration_version
            ),
        )

    def prepare(
        self,
        snapshot: CoverageSnapshot,
    ) -> PreparedCoverageAnalysis:
        independence = self._independence_resolver(snapshot)
        article_independence_keys = self._article_independence_keys(
            snapshot,
            independence,
        )
        unique_sources = {
            row.source.id: row.source
            for row in snapshot.source_rows
        }

        source_type_counts: dict[str, int] = {}
        coverage_scope_counts: dict[str, int] = {}
        country_counts: dict[str, int] = {}

        for source in sorted(
            unique_sources.values(),
            key=lambda value: str(value.id),
        ):
            source_type = self._enum_value(
                source.source_type
            )
            scope = (
                self._enum_value(
                    source.coverage_scope
                )
                if source.coverage_scope is not None
                else None
            )
            country = source.country
            source_type_counts[source_type] = (
                source_type_counts.get(source_type, 0)
                + 1
            )
            if scope is not None:
                coverage_scope_counts[scope] = (
                    coverage_scope_counts.get(scope, 0)
                    + 1
                )
            if country is not None:
                country_counts[country] = (
                    country_counts.get(country, 0)
                    + 1
                )

        source_inputs = []
        for row in sorted(
            snapshot.source_rows,
            key=lambda value: (
                str(value.article.id),
                str(value.source.id),
            ),
        ):
            source_type = self._enum_value(
                row.source.source_type
            )
            scope = (
                self._enum_value(
                    row.source.coverage_scope
                )
                if row.source.coverage_scope is not None
                else None
            )
            source_inputs.append(
                CoverageSourceInput(
                    article_id=row.article.id,
                    source_id=row.source.id,
                    independence_key=(
                        article_independence_keys[row.article.id]
                    ),
                    source_type=source_type,
                    coverage_scope=scope,
                    country=row.source.country,
                    is_signal=(
                        source_type
                        == SourceType.SIGNAL.value
                    ),
                )
            )

        group_inputs = tuple(
            CoverageGroupInput(
                group_id=item.claim_group_id,
                consensus_kind=(
                    self._enum_value(
                        item.consensus_kind
                    )
                ),
                independent_source_count=(
                    item.independent_source_count
                ),
                attributed_perspective_count=(
                    item.attributed_perspective_count
                ),
            )
            for item in snapshot.consensus_summaries
        )
        difference_inputs = tuple(
            CoverageDifferenceInput(
                relation_id=(
                    item.claim_relation_id
                ),
                left_group_id=item.left_group_id,
                right_group_id=item.right_group_id,
            )
            for item
            in snapshot.difference_summaries
        )

        content_sources = [
            item
            for item in source_inputs
            if not item.is_signal
        ]
        signal_sources = [
            item
            for item in source_inputs
            if item.is_signal
        ]
        content_source_ids = {
            item.source_id
            for item in content_sources
        }
        signal_source_ids = {
            item.source_id
            for item in signal_sources
        }
        independent_content_sources = {
            item.independence_key
            for item in content_sources
        }

        metrics = CoverageMetrics(
            article_count=len(
                {
                    row.article.id
                    for row in snapshot.source_rows
                }
            ),
            source_count=len(unique_sources),
            content_source_count=len(
                content_source_ids
            ),
            signal_source_count=len(
                signal_source_ids
            ),
            independent_content_source_count=len(
                independent_content_sources
            ),
            claim_group_count=len(
                group_inputs
            ),
            shared_group_count=sum(
                1
                for item in group_inputs
                if item.consensus_kind
                == "shared"
            ),
            difference_count=len(
                difference_inputs
            ),
            attributed_group_count=sum(
                1
                for item in group_inputs
                if item.attributed_perspective_count
                > 0
            ),
            source_type_counts=(
                source_type_counts
            ),
            coverage_scope_counts=(
                coverage_scope_counts
            ),
            country_counts=country_counts,
        )

        candidate = self.candidate(
            snapshot
        )
        story = (
            snapshot.consensus_snapshot.story
        )
        return PreparedCoverageAnalysis(
            story_id=story.id,
            language_code=story.language_code,
            expected_hash=candidate.input_hash,
            analysis_input=StoryCoverageInput(
                story_id=story.id,
                language_code=story.language_code,
                sources=tuple(source_inputs),
                groups=group_inputs,
                differences=difference_inputs,
            ),
            metrics=metrics,
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedCoverageAnalysis,
        result: StoryCoverageResult,
    ) -> None:
        group_ids = {
            item.group_id
            for item
            in prepared.analysis_input.groups
        }

        seen_gap_keys: set[str] = set()
        for gap in result.gaps:
            if not gap.key.strip():
                raise ValueError(
                    "coverage gap key must not be empty"
                )
            if gap.key in seen_gap_keys:
                raise ValueError(
                    "duplicate coverage gap key"
                )
            if not isinstance(
                gap.gap_kind,
                CoverageGapKind,
            ):
                raise ValueError(
                    "invalid coverage gap kind"
                )
            if gap.observed_count < 0:
                raise ValueError(
                    "coverage observed count "
                    "must not be negative"
                )
            if (
                gap.minimum_expected is not None
                and gap.minimum_expected < 0
            ):
                raise ValueError(
                    "coverage minimum expected "
                    "must not be negative"
                )
            seen_gap_keys.add(gap.key)

        seen_groups: set[UUID] = set()
        for item in result.missing_perspectives:
            if item.group_id not in group_ids:
                raise ValueError(
                    "missing perspective references "
                    "an unknown claim group"
                )
            if item.group_id in seen_groups:
                raise ValueError(
                    "duplicate missing perspective group"
                )
            if (
                item.missing_kind
                != MissingPerspectiveKind
                .NO_ATTRIBUTED_PERSPECTIVE
            ):
                raise ValueError(
                    "invalid missing perspective kind"
                )
            seen_groups.add(
                item.group_id
            )

    def run_provider(
        self,
        prepared: PreparedCoverageAnalysis,
    ) -> StoryCoverageResult:
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
        snapshot: CoverageSnapshot,
        *,
        prepared: PreparedCoverageAnalysis,
        result: StoryCoverageResult,
        processing_run_id: UUID,
        analyzed_at: datetime,
    ) -> None:
        if self.analysis_hash(
            snapshot
        ) != prepared.expected_hash:
            raise ValueError(
                "coverage input identity changed"
            )

        run = db.get(
            StoryProcessingRun,
            processing_run_id,
        )
        if (
            run is None
            or run.finished_at is not None
            or run.outcome is not None
            or run.story_id
            != prepared.story_id
            or run.pipeline
            != StoryPipeline.COVERAGE_ANALYSIS.value
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
                "processing run does not "
                "match coverage identity"
            )

        self._validate_result(
            prepared=prepared,
            result=result,
        )
        self.repository.replace_story_results(
            db,
            story_id=prepared.story_id,
            now=analyzed_at,
        )

        metrics = prepared.metrics
        db.add(
            StoryCoverageSummary(
                story_id=prepared.story_id,
                processing_run_id=(
                    processing_run_id
                ),
                consensus_processing_run_id=(
                    snapshot
                    .consensus_processing_run_id
                ),
                article_count=(
                    metrics.article_count
                ),
                source_count=(
                    metrics.source_count
                ),
                content_source_count=(
                    metrics.content_source_count
                ),
                signal_source_count=(
                    metrics.signal_source_count
                ),
                independent_content_source_count=(
                    metrics
                    .independent_content_source_count
                ),
                claim_group_count=(
                    metrics.claim_group_count
                ),
                shared_group_count=(
                    metrics.shared_group_count
                ),
                difference_count=(
                    metrics.difference_count
                ),
                attributed_group_count=(
                    metrics.attributed_group_count
                ),
                source_type_counts=(
                    metrics.source_type_counts
                ),
                coverage_scope_counts=(
                    metrics.coverage_scope_counts
                ),
                country_counts=(
                    metrics.country_counts
                ),
                analysis_provider=(
                    self.analyzer.provider
                ),
                analysis_version=(
                    self.analyzer.version
                ),
                analyzed_at=analyzed_at,
            )
        )

        for gap in result.gaps:
            db.add(
                StoryCoverageGap(
                    story_id=prepared.story_id,
                    processing_run_id=(
                        processing_run_id
                    ),
                    gap_key=gap.key,
                    gap_kind=gap.gap_kind,
                    observed_count=(
                        gap.observed_count
                    ),
                    minimum_expected=(
                        gap.minimum_expected
                    ),
                    analysis_provider=(
                        self.analyzer.provider
                    ),
                    analysis_version=(
                        self.analyzer.version
                    ),
                    analyzed_at=analyzed_at,
                )
            )

        difference_ids_by_group: dict[
            UUID,
            set[UUID],
        ] = {}
        for item in (
            prepared.analysis_input.differences
        ):
            difference_ids_by_group.setdefault(
                item.left_group_id,
                set(),
            ).add(item.relation_id)
            difference_ids_by_group.setdefault(
                item.right_group_id,
                set(),
            ).add(item.relation_id)

        for item in result.missing_perspectives:
            db.add(
                StoryMissingPerspective(
                    story_id=prepared.story_id,
                    processing_run_id=(
                        processing_run_id
                    ),
                    claim_group_id=(
                        item.group_id
                    ),
                    missing_kind=(
                        item.missing_kind
                    ),
                    contradiction_relation_ids=(
                        sorted(
                            difference_ids_by_group
                            .get(
                                item.group_id,
                                set(),
                            ),
                            key=str,
                        )
                    ),
                    analysis_provider=(
                        self.analyzer.provider
                    ),
                    analysis_version=(
                        self.analyzer.version
                    ),
                    analyzed_at=analyzed_at,
                )
            )
        db.flush()


class CoverageRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: CoverageService | None = None,
        processing_repository: StoryProcessingRepository | None = None,
        story_repository: StoryRepository | None = None,
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
            or retry_max_seconds
            < retry_base_seconds
        ):
            raise ValueError(
                "coverage worker timing "
                "settings are invalid"
            )
        self.session_factory = (
            session_factory
        )
        self.service = (
            service
            or CoverageService()
        )
        self.processing_repository = (
            processing_repository
            or StoryProcessingRepository()
        )
        self.story_repository = (
            story_repository
            or StoryRepository()
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
            or (lambda: datetime.now(UTC))
        )

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[StoryProcessingClaim]:
        claimed: list[
            StoryProcessingClaim
        ] = []
        page_size = max(
            50,
            limit * 4,
        )
        last_created_at = None
        last_story_id = None

        while len(claimed) < limit:
            stories = (
                self.service.repository
                .list_candidate_stories(
                    db,
                    after_created_at=(
                        last_created_at
                    ),
                    after_id=last_story_id,
                    limit=page_size,
                )
            )
            if not stories:
                break

            candidates = []
            for story in stories:
                snapshot = (
                    self.service.load_snapshot(
                        db,
                        story_id=story.id,
                    )
                )
                if snapshot is not None:
                    candidates.append(
                        self.service.candidate(
                            snapshot
                        )
                    )

            if candidates:
                claimed.extend(
                    self.processing_repository
                    .claim_candidates(
                        db,
                        pipeline=(
                            StoryPipeline
                            .COVERAGE_ANALYSIS
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
                                    self
                                    .claim_ttl_seconds
                                )
                            )
                        ),
                        limit=(
                            limit
                            - len(claimed)
                        ),
                    )
                )

            last = stories[-1]
            last_created_at = (
                last.created_at
            )
            last_story_id = last.id
            if len(stories) < page_size:
                break

        return claimed

    def run_pending(
        self,
        *,
        limit: int,
    ) -> CoverageBatchResult:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        processed = 0
        skipped = 0
        failed = 0

        with self.session_factory() as db:
            now = self.clock()
            with db.begin():
                stale = (
                    self.service.repository
                    .deactivate_without_active_consensus(
                        db,
                        now=now,
                    )
                )
                if stale:
                    self.processing_repository.invalidate_processed(
                        db,
                        pipeline=(
                            StoryPipeline
                            .COVERAGE_ANALYSIS
                            .value
                        ),
                        story_ids=stale,
                    )

            with db.begin():
                claimed = self._claim_pending(
                    db,
                    limit=limit,
                    now=now,
                )

            for claim in claimed:
                try:
                    with db.begin():
                        snapshot = (
                            self.service
                            .load_snapshot(
                                db,
                                story_id=(
                                    claim.story_id
                                ),
                            )
                        )
                        if snapshot is None:
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=claim.run_id,
                                worker_id=(
                                    self.worker_id
                                ),
                                now=self.clock(),
                                reason=(
                                    "coverage upstream "
                                    "generation incomplete"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                snapshot
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
                                run_id=claim.run_id,
                                worker_id=(
                                    self.worker_id
                                ),
                                now=self.clock(),
                                reason=(
                                    "coverage input "
                                    "changed before provider"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = (
                            self.service.prepare(
                                snapshot
                            )
                        )

                    result = (
                        self.service.run_provider(
                            prepared
                        )
                    )

                    with db.begin():
                        final_now = self.clock()
                        self.story_repository.acquire_processing_coordination_lock(
                            db
                        )
                        if not self.processing_repository.heartbeat(
                            db,
                            state_id=(
                                claim.state_id
                            ),
                            run_id=claim.run_id,
                            worker_id=(
                                self.worker_id
                            ),
                            now=final_now,
                            claim_expires_at=(
                                final_now
                                + timedelta(
                                    seconds=(
                                        self
                                        .claim_ttl_seconds
                                    )
                                )
                            ),
                        ):
                            raise StoryProcessingLeaseLostError(
                                "coverage lease lost"
                            )

                        consensus_story = (
                            self.service
                            .consensus_service
                            .claim_repository
                            .get_story(
                                db,
                                story_id=(
                                    claim.story_id
                                ),
                            )
                        )
                        if consensus_story is None:
                            raise StoryProcessingLeaseLostError(
                                "story inactive "
                                "during coverage"
                            )

                        self.story_repository.acquire_clustering_lock(
                            db,
                            language_code=(
                                consensus_story
                                .language_code
                            ),
                        )

                        snapshot = (
                            self.service
                            .load_snapshot(
                                db,
                                story_id=(
                                    claim.story_id
                                ),
                                for_update=True,
                                lock_articles=True,
                            )
                        )
                        if snapshot is None:
                            self.processing_repository.skip(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=claim.run_id,
                                worker_id=(
                                    self.worker_id
                                ),
                                now=final_now,
                                reason=(
                                    "coverage upstream "
                                    "generation became "
                                    "incomplete"
                                ),
                            )
                            skipped += 1
                            continue

                        current = (
                            self.service.candidate(
                                snapshot
                            )
                        )
                        if (
                            not claim
                            .matches_candidate(
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
                                run_id=claim.run_id,
                                worker_id=(
                                    self.worker_id
                                ),
                                now=final_now,
                                reason=(
                                    "coverage input "
                                    "changed during "
                                    "provider"
                                ),
                            )
                            skipped += 1
                            continue

                        self.service.persist_result(
                            db,
                            snapshot,
                            prepared=prepared,
                            result=result,
                            processing_run_id=(
                                claim.run_id
                            ),
                            analyzed_at=(
                                final_now
                            ),
                        )
                        self.processing_repository.complete(
                            db,
                            state_id=(
                                claim.state_id
                            ),
                            run_id=claim.run_id,
                            worker_id=(
                                self.worker_id
                            ),
                            now=final_now,
                        )
                    processed += 1

                except StoryProcessingLeaseLostError as exc:
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
                    with db.begin():
                        try:
                            self.processing_repository.fail(
                                db,
                                state_id=(
                                    claim.state_id
                                ),
                                run_id=claim.run_id,
                                worker_id=(
                                    self.worker_id
                                ),
                                now=self.clock(),
                                retry_after=(
                                    self.clock()
                                    + timedelta(
                                        seconds=delay
                                    )
                                ),
                                error_code=(
                                    type(exc)
                                    .__name__
                                ),
                                error_message=(
                                    str(exc)[:2000]
                                ),
                            )
                        except StoryProcessingLeaseLostError:
                            self.processing_repository.mark_lease_lost(
                                db,
                                run_id=(
                                    claim.run_id
                                ),
                                now=self.clock(),
                                error_message=(
                                    str(exc)
                                ),
                            )
                    failed += 1
                    logger.exception(
                        "Coverage analysis failed",
                        extra={
                            "story_id": (
                                str(
                                    claim.story_id
                                )
                            ),
                            "processing_run_id": (
                                str(
                                    claim.run_id
                                )
                            ),
                        },
                    )

        return CoverageBatchResult(
            selected=len(claimed),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
