import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.consensus.provider import (
    ClaimDifferenceInput,
    ClaimGroupConsensusInput,
    ConsensusAnalyzer,
    ConsensusKind,
    DifferenceKind,
    StoryConsensusInput,
    StoryConsensusResult,
)
from app.consensus.rule_based import RuleBasedConsensusAnalyzer
from app.enums.story_pipeline import StoryPipeline
from app.models.consensus import (
    StoryConsensusSummary,
    StoryDifferenceSummary,
)
from app.models.story import Story
from app.models.source_dependency import ArticleProvenance, SourceRelation
from app.models.story_processing import StoryProcessingRun
from app.repositories.claim_relation import (
    ClaimRelationRepository,
    EligibleStoryMembership,
)
from app.repositories.consensus import (
    ConsensusGroupRow,
    ConsensusRepository,
)
from app.repositories.source_dependency import SourceDependencyRepository
from app.repositories.story import StoryRepository
from app.services.source_independence import (
    SourceIndependenceResolver,
    counts_as_independent_confirmation,
)
from app.repositories.story_processing import (
    StoryProcessingCandidate,
    StoryProcessingClaim,
    StoryProcessingLeaseLostError,
    StoryProcessingRepository,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConsensusBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class ConsensusSnapshot:
    story: Story
    memberships: tuple[EligibleStoryMembership, ...]
    rows: tuple[ConsensusGroupRow, ...]
    evidence: tuple[tuple[object, object], ...]
    perspectives: tuple[object, ...]
    relations: tuple[object, ...]
    source_relations: tuple[SourceRelation, ...]
    article_provenance: tuple[ArticleProvenance, ...]


@dataclass(frozen=True, slots=True)
class PreparedConsensusAnalysis:
    story_id: UUID
    language_code: str | None
    expected_hash: str
    analysis_input: StoryConsensusInput


class ConsensusService:
    CONFIG_VERSION = "4"

    def __init__(
        self,
        analyzer: ConsensusAnalyzer | None = None,
        repository: ConsensusRepository | None = None,
        claim_repository: ClaimRelationRepository | None = None,
        dependency_repository: SourceDependencyRepository | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.analyzer = analyzer or RuleBasedConsensusAnalyzer()
        self.repository = repository or ConsensusRepository()
        self.claim_repository = claim_repository or ClaimRelationRepository()
        self.dependency_repository = (
            dependency_repository
            or SourceDependencyRepository()
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

    def load_snapshot(
        self,
        db: Session,
        *,
        story_id: UUID,
        for_update: bool = False,
        lock_articles: bool = False,
    ) -> ConsensusSnapshot | None:
        story = self.claim_repository.get_story(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if story is None:
            return None

        memberships = self.claim_repository.load_eligible_memberships(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if not memberships:
            return None

        article_ids = [item.article.id for item in memberships]
        if lock_articles:
            self.claim_repository.lock_articles(
                db,
                article_ids=article_ids,
            )
            memberships = self.claim_repository.load_eligible_memberships(
                db,
                story_id=story_id,
                for_update=for_update,
            )
            article_ids = [item.article.id for item in memberships]
            if not article_ids:
                return None

        claims = self.claim_repository.load_active_claims(
            db,
            article_ids=article_ids,
            for_update=for_update,
        )
        if not claims:
            return None

        rows = self.repository.load_group_rows(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if not rows:
            return None

        active_claim_ids = {claim.id for claim in claims}
        grouped_claim_ids = {row.claim.id for row in rows}
        if grouped_claim_ids != active_claim_ids:
            return None

        representative_ids = {
            row.group.representative_claim_id
            for row in rows
        }
        if not representative_ids.issubset(grouped_claim_ids):
            return None

        evidence = self.repository.load_active_evidence(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        evidence_claim_ids = {
            evidence_item.claim_id
            for _, evidence_item in evidence
        }
        if evidence_claim_ids != grouped_claim_ids:
            return None

        current_group_by_claim = {
            row.claim.id: row.group.id
            for row in rows
        }
        if any(
            link.claim_group_id
            != current_group_by_claim.get(
                evidence_item.claim_id
            )
            for link, evidence_item in evidence
        ):
            return None

        perspectives = self.repository.load_active_perspectives(
            db,
            claim_ids=sorted(
                grouped_claim_ids,
                key=str,
            ),
            for_update=for_update,
        )
        relations = self.repository.load_relations(
            db,
            story_id=story_id,
            for_update=for_update,
        )

        group_ids = {row.group.id for row in rows}
        if any(
            relation.left_group_id not in group_ids
            or relation.right_group_id not in group_ids
            for relation in relations
        ):
            return None

        article_provenance = (
            self.dependency_repository
            .load_verified_article_provenance(
                db,
                article_ids=article_ids,
            )
        )
        dependency_source_ids = {
            row.source.id
            for row in rows
        }
        dependency_source_ids.update(
            item.upstream_source_id
            for item in article_provenance
        )
        source_relations = (
            self.dependency_repository
            .load_independence_relations(
                db,
                seed_source_ids=dependency_source_ids,
            )
        )

        return ConsensusSnapshot(
            story=story,
            memberships=tuple(memberships),
            rows=tuple(rows),
            evidence=tuple(evidence),
            perspectives=tuple(perspectives),
            relations=tuple(relations),
            source_relations=tuple(source_relations),
            article_provenance=tuple(article_provenance),
        )

    @staticmethod
    def _enum_value(value) -> str:
        return (
            value.value
            if hasattr(value, "value")
            else str(value)
        )

    @staticmethod
    def _independence_resolver(
        snapshot: ConsensusSnapshot,
    ) -> SourceIndependenceResolver:
        return SourceIndependenceResolver(
            relations=snapshot.source_relations,
            provenance=snapshot.article_provenance,
        )

    @staticmethod
    def _article_independence_keys(
        snapshot: ConsensusSnapshot,
        resolver: SourceIndependenceResolver,
    ) -> dict[UUID, str]:
        articles = {
            row.article.id: (
                row.article.id,
                row.source.id,
                row.article.published_at,
            )
            for row in snapshot.rows
        }
        return resolver.article_component_keys(
            articles=tuple(
                articles[article_id]
                for article_id in sorted(articles, key=str)
            )
        )

    def analysis_hash(
        self,
        snapshot: ConsensusSnapshot,
    ) -> str:
        independence = self._independence_resolver(snapshot)
        article_independence_keys = self._article_independence_keys(
            snapshot,
            independence,
        )
        membership_identity = [
            [
                str(item.membership.id),
                str(item.membership.processing_run_id),
                str(item.membership.article_id),
                str(item.source_id),
                item.membership.article_time.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
            ]
            for item in snapshot.memberships
        ]
        group_identity = [
            [
                str(row.group.id),
                str(row.group.processing_run_id),
                row.group.group_hash,
                str(row.group.representative_claim_id),
                str(row.member.id),
                str(row.claim.id),
                str(row.claim.processing_run_id),
                row.claim.claim_hash,
                str(row.article.id),
                str(row.source.id),
                self._enum_value(row.source.source_type),
                article_independence_keys[row.article.id],
            ]
            for row in snapshot.rows
        ]
        evidence_identity = [
            [
                str(link.id),
                str(link.processing_run_id),
                str(link.claim_group_id),
                self._enum_value(link.relation_kind),
                str(item.id),
                str(item.processing_run_id),
                str(item.claim_id),
                str(item.source_id),
                self._enum_value(item.evidence_kind),
                item.evidence_hash,
            ]
            for link, item in snapshot.evidence
        ]
        perspective_identity = [
            [
                str(item.id),
                str(item.processing_run_id),
                str(item.claim_id),
                (
                    str(item.holder_entity_id)
                    if item.holder_entity_id is not None
                    else ""
                ),
                self._enum_value(item.perspective_kind),
            ]
            for item in snapshot.perspectives
        ]
        relation_identity = [
            [
                str(item.id),
                str(item.processing_run_id),
                str(item.left_group_id),
                str(item.right_group_id),
                self._enum_value(item.relation_kind),
            ]
            for item in snapshot.relations
        ]
        source_relation_identity = [
            [
                str(item.id),
                str(item.source_id),
                str(item.related_source_id),
                self._enum_value(item.relation_kind),
                (
                    item.valid_from.isoformat()
                    if item.valid_from is not None
                    else ""
                ),
                (
                    item.valid_to.isoformat()
                    if item.valid_to is not None
                    else ""
                ),
            ]
            for item in snapshot.source_relations
        ]
        provenance_identity = [
            [
                str(item.id),
                str(item.article_id),
                str(item.upstream_source_id),
                (
                    str(item.upstream_article_id)
                    if item.upstream_article_id is not None
                    else ""
                ),
                self._enum_value(item.relation_kind),
                item.confidence,
                self._enum_value(item.detection_method),
                item.verified,
            ]
            for item in snapshot.article_provenance
        ]
        payload = [
            str(snapshot.story.id),
            snapshot.story.language_code or "",
            membership_identity,
            group_identity,
            evidence_identity,
            perspective_identity,
            relation_identity,
            source_relation_identity,
            provenance_identity,
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
        snapshot: ConsensusSnapshot,
    ) -> StoryProcessingCandidate:
        return StoryProcessingCandidate(
            story_id=snapshot.story.id,
            input_hash=self.analysis_hash(snapshot),
            provider=self.analyzer.provider,
            provider_version=self.analyzer.version,
            configuration_version=self.processing_configuration_version,
        )

    def prepare(
        self,
        snapshot: ConsensusSnapshot,
    ) -> PreparedConsensusAnalysis:
        independence = self._independence_resolver(snapshot)
        article_independence_keys = self._article_independence_keys(
            snapshot,
            independence,
        )
        rows_by_group: dict[UUID, list[ConsensusGroupRow]] = {}
        for row in snapshot.rows:
            rows_by_group.setdefault(
                row.group.id,
                [],
            ).append(row)

        evidence_by_group: dict[UUID, list[tuple[object, object]]] = {}
        for link, item in snapshot.evidence:
            evidence_by_group.setdefault(
                link.claim_group_id,
                [],
            ).append((link, item))

        perspectives_by_claim: dict[UUID, int] = {}
        for perspective in snapshot.perspectives:
            if perspective.holder_entity_id is not None:
                perspectives_by_claim[perspective.claim_id] = (
                    perspectives_by_claim.get(
                        perspective.claim_id,
                        0,
                    )
                    + 1
                )

        groups = []
        group_input_by_id: dict[UUID, ClaimGroupConsensusInput] = {}
        for group_id, rows in rows_by_group.items():
            group = rows[0].group
            representative = next(
                row.claim
                for row in rows
                if row.claim.id == group.representative_claim_id
            )
            independent_sources = {
                article_independence_keys[row.article.id]
                for row in rows
                if counts_as_independent_confirmation(
                    row.source.source_type
                )
            }
            group_evidence = evidence_by_group.get(
                group_id,
                [],
            )
            evidence_sources = {
                item.source_id
                for _, item in group_evidence
            }
            value = ClaimGroupConsensusInput(
                group_id=group_id,
                representative_claim_id=group.representative_claim_id,
                representative_claim_text=representative.claim_text,
                claim_count=len(
                    {
                        row.claim.id
                        for row in rows
                    }
                ),
                article_count=len(
                    {
                        row.article.id
                        for row in rows
                    }
                ),
                independent_source_count=len(
                    independent_sources
                ),
                evidence_item_count=len(group_evidence),
                evidence_source_count=len(evidence_sources),
                attributed_perspective_count=sum(
                    perspectives_by_claim.get(
                        row.claim.id,
                        0,
                    )
                    for row in rows
                ),
            )
            groups.append(value)
            group_input_by_id[group_id] = value

        differences = tuple(
            ClaimDifferenceInput(
                relation_id=relation.id,
                left_group_id=relation.left_group_id,
                right_group_id=relation.right_group_id,
                left_claim_text=(
                    group_input_by_id[
                        relation.left_group_id
                    ].representative_claim_text
                ),
                right_claim_text=(
                    group_input_by_id[
                        relation.right_group_id
                    ].representative_claim_text
                ),
                left_independent_source_count=(
                    group_input_by_id[
                        relation.left_group_id
                    ].independent_source_count
                ),
                right_independent_source_count=(
                    group_input_by_id[
                        relation.right_group_id
                    ].independent_source_count
                ),
                left_evidence_source_count=(
                    group_input_by_id[
                        relation.left_group_id
                    ].evidence_source_count
                ),
                right_evidence_source_count=(
                    group_input_by_id[
                        relation.right_group_id
                    ].evidence_source_count
                ),
            )
            for relation in snapshot.relations
        )

        candidate = self.candidate(snapshot)
        return PreparedConsensusAnalysis(
            story_id=snapshot.story.id,
            language_code=snapshot.story.language_code,
            expected_hash=candidate.input_hash,
            analysis_input=StoryConsensusInput(
                story_id=snapshot.story.id,
                language_code=snapshot.story.language_code,
                groups=tuple(
                    sorted(
                        groups,
                        key=lambda item: str(item.group_id),
                    )
                ),
                differences=differences,
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedConsensusAnalysis,
        result: StoryConsensusResult,
    ) -> None:
        expected_groups = {
            item.group_id
            for item in prepared.analysis_input.groups
        }
        actual_groups = {
            item.group_id
            for item in result.consensus
        }
        if actual_groups != expected_groups:
            raise ValueError(
                "consensus result must cover every claim group exactly once"
            )
        if len(actual_groups) != len(result.consensus):
            raise ValueError("duplicate consensus group")
        if any(
            not isinstance(item.consensus_kind, ConsensusKind)
            for item in result.consensus
        ):
            raise ValueError("invalid consensus kind")

        expected_relations = {
            item.relation_id
            for item in prepared.analysis_input.differences
        }
        actual_relations = {
            item.relation_id
            for item in result.differences
        }
        if actual_relations != expected_relations:
            raise ValueError(
                "difference result must cover every contradiction exactly once"
            )
        if len(actual_relations) != len(result.differences):
            raise ValueError("duplicate difference relation")
        if any(
            item.difference_kind != DifferenceKind.CONTRADICTION
            for item in result.differences
        ):
            raise ValueError("invalid difference kind")

    def run_provider(
        self,
        prepared: PreparedConsensusAnalysis,
    ) -> StoryConsensusResult:
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
        snapshot: ConsensusSnapshot,
        *,
        prepared: PreparedConsensusAnalysis,
        result: StoryConsensusResult,
        processing_run_id: UUID,
        analyzed_at: datetime,
    ) -> None:
        if self.analysis_hash(snapshot) != prepared.expected_hash:
            raise ValueError(
                "consensus input identity changed after preparation"
            )
        run = db.get(
            StoryProcessingRun,
            processing_run_id,
        )
        if (
            run is None
            or run.finished_at is not None
            or run.outcome is not None
            or run.story_id != snapshot.story.id
            or run.pipeline != StoryPipeline.CONSENSUS_ANALYSIS.value
            or run.input_hash != prepared.expected_hash
            or run.provider != self.analyzer.provider
            or run.provider_version != self.analyzer.version
            or run.configuration_version
            != self.processing_configuration_version
        ):
            raise ValueError(
                "processing run does not match consensus identity"
            )

        self._validate_result(
            prepared=prepared,
            result=result,
        )
        group_input = {
            item.group_id: item
            for item in prepared.analysis_input.groups
        }
        difference_input = {
            item.relation_id: item
            for item in prepared.analysis_input.differences
        }

        self.repository.replace_story_results(
            db,
            story_id=snapshot.story.id,
            now=analyzed_at,
        )

        for item in result.consensus:
            source = group_input[item.group_id]
            db.add(
                StoryConsensusSummary(
                    story_id=snapshot.story.id,
                    processing_run_id=processing_run_id,
                    claim_group_id=item.group_id,
                    consensus_kind=item.consensus_kind,
                    claim_count=source.claim_count,
                    article_count=source.article_count,
                    independent_source_count=source.independent_source_count,
                    evidence_item_count=source.evidence_item_count,
                    evidence_source_count=source.evidence_source_count,
                    attributed_perspective_count=source.attributed_perspective_count,
                    analysis_provider=self.analyzer.provider,
                    analysis_version=self.analyzer.version,
                    analyzed_at=analyzed_at,
                )
            )

        relation_by_id = {
            relation.id: relation
            for relation in snapshot.relations
        }
        for item in result.differences:
            source = difference_input[item.relation_id]
            relation = relation_by_id[item.relation_id]
            db.add(
                StoryDifferenceSummary(
                    story_id=snapshot.story.id,
                    processing_run_id=processing_run_id,
                    claim_relation_id=item.relation_id,
                    left_group_id=relation.left_group_id,
                    right_group_id=relation.right_group_id,
                    difference_kind=item.difference_kind,
                    left_independent_source_count=source.left_independent_source_count,
                    right_independent_source_count=source.right_independent_source_count,
                    left_evidence_source_count=source.left_evidence_source_count,
                    right_evidence_source_count=source.right_evidence_source_count,
                    analysis_provider=self.analyzer.provider,
                    analysis_version=self.analyzer.version,
                    analyzed_at=analyzed_at,
                )
            )
        db.flush()


class ConsensusRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: ConsensusService | None = None,
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
            or retry_max_seconds < retry_base_seconds
        ):
            raise ValueError(
                "consensus worker timing settings are invalid"
            )
        self.session_factory = session_factory
        self.service = service or ConsensusService()
        self.processing_repository = (
            processing_repository or StoryProcessingRepository()
        )
        self.story_repository = story_repository or StoryRepository()
        self.claim_ttl_seconds = claim_ttl_seconds
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self.worker_id = worker_id or str(uuid4())
        self.clock = clock or (lambda: datetime.now(UTC))

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[StoryProcessingClaim]:
        claimed: list[StoryProcessingClaim] = []
        page_size = max(50, limit * 4)
        last_created_at = None
        last_story_id = None

        while len(claimed) < limit:
            stories = self.service.repository.list_candidate_stories(
                db,
                after_created_at=last_created_at,
                after_id=last_story_id,
                limit=page_size,
            )
            if not stories:
                break

            candidates = []
            for story in stories:
                snapshot = self.service.load_snapshot(
                    db,
                    story_id=story.id,
                )
                if snapshot is not None:
                    candidates.append(
                        self.service.candidate(snapshot)
                    )

            if candidates:
                claimed.extend(
                    self.processing_repository.claim_candidates(
                        db,
                        pipeline=StoryPipeline.CONSENSUS_ANALYSIS.value,
                        candidates=candidates,
                        worker_id=self.worker_id,
                        now=now,
                        claim_expires_at=(
                            now
                            + timedelta(
                                seconds=self.claim_ttl_seconds
                            )
                        ),
                        limit=limit - len(claimed),
                    )
                )

            last = stories[-1]
            last_created_at = last.created_at
            last_story_id = last.id
            if len(stories) < page_size:
                break

        return claimed

    def run_pending(
        self,
        *,
        limit: int,
    ) -> ConsensusBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        processed = skipped = failed = 0

        with self.session_factory() as db:
            now = self.clock()
            with db.begin():
                stale = self.service.repository.deactivate_without_active_groups(
                    db,
                    now=now,
                )
                if stale:
                    self.processing_repository.invalidate_processed(
                        db,
                        pipeline=StoryPipeline.CONSENSUS_ANALYSIS.value,
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
                        snapshot = self.service.load_snapshot(
                            db,
                            story_id=claim.story_id,
                        )
                        if snapshot is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason="consensus upstream generation incomplete",
                            )
                            skipped += 1
                            continue
                        current = self.service.candidate(snapshot)
                        if not claim.matches_candidate(current):
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                reason="consensus input changed before provider",
                            )
                            skipped += 1
                            continue
                        prepared = self.service.prepare(snapshot)

                    result = self.service.run_provider(prepared)

                    with db.begin():
                        final_now = self.clock()
                        self.story_repository.acquire_processing_coordination_lock(
                            db
                        )
                        if not self.processing_repository.heartbeat(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=final_now,
                            claim_expires_at=(
                                final_now
                                + timedelta(
                                    seconds=self.claim_ttl_seconds
                                )
                            ),
                        ):
                            raise StoryProcessingLeaseLostError(
                                "consensus lease lost"
                            )

                        story = self.service.claim_repository.get_story(
                            db,
                            story_id=claim.story_id,
                        )
                        if story is None:
                            raise StoryProcessingLeaseLostError(
                                "story inactive during consensus"
                            )
                        self.story_repository.acquire_clustering_lock(
                            db,
                            language_code=story.language_code,
                        )
                        snapshot = self.service.load_snapshot(
                            db,
                            story_id=claim.story_id,
                            for_update=True,
                            lock_articles=True,
                        )
                        if snapshot is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=final_now,
                                reason="consensus upstream generation became incomplete",
                            )
                            skipped += 1
                            continue
                        current = self.service.candidate(snapshot)
                        if (
                            not claim.matches_candidate(current)
                            or current.input_hash != prepared.expected_hash
                        ):
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=final_now,
                                reason="consensus input changed during provider",
                            )
                            skipped += 1
                            continue

                        self.service.persist_result(
                            db,
                            snapshot,
                            prepared=prepared,
                            result=result,
                            processing_run_id=claim.run_id,
                            analyzed_at=final_now,
                        )
                        self.processing_repository.complete(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
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
                        * (2 ** max(claim.attempt_number - 1, 0)),
                    )
                    with db.begin():
                        try:
                            self.processing_repository.fail(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=self.clock(),
                                retry_after=(
                                    self.clock()
                                    + timedelta(seconds=delay)
                                ),
                                error_code=type(exc).__name__,
                                error_message=str(exc)[:2000],
                            )
                        except StoryProcessingLeaseLostError:
                            self.processing_repository.mark_lease_lost(
                                db,
                                run_id=claim.run_id,
                                now=self.clock(),
                                error_message=str(exc),
                            )
                    failed += 1
                    logger.exception(
                        "Consensus analysis failed",
                        extra={
                            "story_id": str(claim.story_id),
                            "processing_run_id": str(claim.run_id),
                        },
                    )

        return ConsensusBatchResult(
            selected=len(claimed),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
