import hashlib
import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.enums.story_pipeline import StoryPipeline
from app.evidence.provider import (
    EvidenceAnalyzer,
    EvidenceKind,
    EvidenceRelationKind,
    StoryEvidenceAnalysisInput,
    StoryEvidenceAnalysisResult,
    ClaimEvidenceInput,
)
from app.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.models.evidence import StoryClaimEvidence, StoryEvidence
from app.models.story import Story
from app.models.story_processing import StoryProcessingRun
from app.repositories.claim_relation import (
    ClaimRelationRepository,
    EligibleStoryMembership,
)
from app.repositories.evidence import EvidenceClaimRow, EvidenceRepository
from app.repositories.story import StoryRepository
from app.repositories.story_processing import (
    StoryProcessingCandidate,
    StoryProcessingClaim,
    StoryProcessingLeaseLostError,
    StoryProcessingRepository,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EvidenceBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    story: Story
    memberships: tuple[EligibleStoryMembership, ...]
    rows: tuple[EvidenceClaimRow, ...]
    direct_quotes: tuple[
        tuple[UUID, tuple[str, ...]],
        ...
    ]


@dataclass(frozen=True, slots=True)
class PreparedEvidenceAnalysis:
    story_id: UUID
    language_code: str | None
    expected_hash: str
    analysis_input: StoryEvidenceAnalysisInput


class EvidenceService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        analyzer: EvidenceAnalyzer | None = None,
        repository: EvidenceRepository | None = None,
        claim_repository: ClaimRelationRepository | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.analyzer = analyzer or RuleBasedEvidenceAnalyzer()
        self.repository = repository or EvidenceRepository()
        self.claim_repository = claim_repository or ClaimRelationRepository()
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
    ) -> EvidenceSnapshot | None:
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

        rows = self.repository.load_claim_rows(
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

        direct_quotes = self.repository.load_direct_quotes(
            db,
            claim_ids=sorted(
                grouped_claim_ids,
                key=str,
            ),
        )

        return EvidenceSnapshot(
            story=story,
            memberships=tuple(memberships),
            rows=tuple(rows),
            direct_quotes=tuple(
                sorted(
                    direct_quotes.items(),
                    key=lambda item: str(item[0]),
                )
            ),
        )

    def analysis_hash(
        self,
        snapshot: EvidenceSnapshot,
    ) -> str:
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
            for item in sorted(
                snapshot.memberships,
                key=lambda value: (
                    value.membership.article_time,
                    str(value.membership.article_id),
                    str(value.membership.id),
                ),
            )
        ]

        direct_quote_map = dict(
            snapshot.direct_quotes
        )

        evidence_input_identity = [
            [
                str(row.group.id),
                str(row.group.processing_run_id),
                row.group.group_hash,
                str(row.group.representative_claim_id),
                row.group.confidence,
                str(row.member.id),
                str(row.claim.id),
                str(row.claim.processing_run_id),
                row.claim.claim_hash,
                row.claim.normalized_claim,
                row.claim.confidence,
                str(row.article.id),
                row.article.content_hash,
                row.article.normalized_title or "",
                row.article.normalized_text or "",
                row.article.link or "",
                str(row.source.id),
                row.source.source_type.value,
                list(
                    direct_quote_map.get(
                        row.claim.id,
                        (),
                    )
                ),
            ]
            for row in snapshot.rows
        ]

        payload = [
            str(snapshot.story.id),
            snapshot.story.language_code or "",
            membership_identity,
            evidence_input_identity,
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
        snapshot: EvidenceSnapshot,
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
        snapshot: EvidenceSnapshot,
    ) -> PreparedEvidenceAnalysis:
        direct_quote_map = dict(
            snapshot.direct_quotes
        )
        claims = tuple(
            ClaimEvidenceInput(
                claim_id=row.claim.id,
                claim_group_id=row.group.id,
                article_id=row.article.id,
                source_id=row.source.id,
                source_type=row.source.source_type.value,
                claim_text=row.claim.claim_text,
                normalized_claim=row.claim.normalized_claim,
                article_title=row.article.title,
                article_text=row.article.normalized_text or "",
                article_url=row.article.link,
                direct_quote_texts=(
                    direct_quote_map.get(
                        row.claim.id,
                        (),
                    )
                ),
            )
            for row in snapshot.rows
        )
        candidate = self.candidate(snapshot)
        return PreparedEvidenceAnalysis(
            story_id=snapshot.story.id,
            language_code=snapshot.story.language_code,
            expected_hash=candidate.input_hash,
            analysis_input=StoryEvidenceAnalysisInput(
                story_id=snapshot.story.id,
                language_code=snapshot.story.language_code,
                claims=claims,
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedEvidenceAnalysis,
        result: StoryEvidenceAnalysisResult,
    ) -> None:
        input_by_claim = {
            item.claim_id: item
            for item in prepared.analysis_input.claims
        }
        evidence_by_key = {}
        seen_evidence: set[
            tuple[UUID, EvidenceKind, str]
        ] = set()

        for item in result.evidence:
            if not item.key.strip():
                raise ValueError("evidence key must not be empty")
            if item.key in evidence_by_key:
                raise ValueError("duplicate evidence key")
            if item.claim_id not in input_by_claim:
                raise ValueError("evidence references an unknown claim")
            if not isinstance(item.evidence_kind, EvidenceKind):
                raise ValueError("evidence kind is invalid")
            if not item.evidence_text.strip():
                raise ValueError("evidence text must not be empty")
            if (
                not math.isfinite(item.confidence)
                or not 0 <= item.confidence <= 1
            ):
                raise ValueError(
                    "evidence confidence must be between zero and one"
                )
            semantic_key = (
                item.claim_id,
                item.evidence_kind,
                item.evidence_text.strip(),
            )
            if semantic_key in seen_evidence:
                raise ValueError(
                    "duplicate semantic evidence item"
                )
            seen_evidence.add(semantic_key)
            evidence_by_key[item.key] = item

        linked_keys: set[str] = set()
        for link in result.links:
            if link.evidence_key not in evidence_by_key:
                raise ValueError("evidence link references an unknown item")
            if link.evidence_key in linked_keys:
                raise ValueError("evidence item has more than one claim-group link")
            if not isinstance(link.relation_kind, EvidenceRelationKind):
                raise ValueError("evidence relation kind is invalid")
            if (
                not math.isfinite(link.confidence)
                or not 0 <= link.confidence <= 1
            ):
                raise ValueError(
                    "evidence link confidence must be between zero and one"
                )

            evidence_item = evidence_by_key[link.evidence_key]
            expected_group = input_by_claim[
                evidence_item.claim_id
            ].claim_group_id
            if link.claim_group_id != expected_group:
                raise ValueError(
                    "evidence item is linked to the wrong claim group"
                )
            linked_keys.add(link.evidence_key)

        if linked_keys != set(evidence_by_key):
            raise ValueError(
                "every evidence item must have exactly one claim-group link"
            )

    def run_provider(
        self,
        prepared: PreparedEvidenceAnalysis,
    ) -> StoryEvidenceAnalysisResult:
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
        snapshot: EvidenceSnapshot,
        *,
        prepared: PreparedEvidenceAnalysis,
        result: StoryEvidenceAnalysisResult,
        processing_run_id: UUID,
        analyzed_at: datetime,
    ) -> None:
        if snapshot.story.id != prepared.story_id:
            raise ValueError(
                "prepared evidence analysis belongs to another story"
            )
        if self.analysis_hash(snapshot) != prepared.expected_hash:
            raise ValueError(
                "story evidence input identity changed after preparation"
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
            or run.pipeline != StoryPipeline.EVIDENCE_ANALYSIS.value
            or run.input_hash != prepared.expected_hash
            or run.provider != self.analyzer.provider
            or run.provider_version != self.analyzer.version
            or run.configuration_version
            != self.processing_configuration_version
        ):
            raise ValueError(
                "processing run does not match evidence identity"
            )

        self._validate_result(
            prepared=prepared,
            result=result,
        )

        input_by_claim = {
            item.claim_id: item
            for item in prepared.analysis_input.claims
        }

        self.repository.replace_story_results(
            db,
            story_id=snapshot.story.id,
            now=analyzed_at,
        )

        evidence_by_key: dict[str, StoryEvidence] = {}
        for item in sorted(
            result.evidence,
            key=lambda value: value.key,
        ):
            source = input_by_claim[item.claim_id]
            evidence_hash = hashlib.sha256(
                (
                    item.evidence_kind.value
                    + "\0"
                    + item.evidence_text.strip()
                ).encode("utf-8")
            ).hexdigest()
            evidence = StoryEvidence(
                story_id=snapshot.story.id,
                processing_run_id=processing_run_id,
                claim_id=item.claim_id,
                article_id=source.article_id,
                source_id=source.source_id,
                evidence_kind=item.evidence_kind,
                evidence_text=item.evidence_text,
                evidence_hash=evidence_hash,
                confidence=item.confidence,
                analysis_provider=self.analyzer.provider,
                analysis_version=self.analyzer.version,
                analyzed_at=analyzed_at,
            )
            db.add(evidence)
            db.flush()
            evidence_by_key[item.key] = evidence

        for link in sorted(
            result.links,
            key=lambda value: (
                str(value.claim_group_id),
                value.evidence_key,
                value.relation_kind.value,
            ),
        ):
            db.add(
                StoryClaimEvidence(
                    story_id=snapshot.story.id,
                    processing_run_id=processing_run_id,
                    claim_group_id=link.claim_group_id,
                    evidence_id=evidence_by_key[link.evidence_key].id,
                    relation_kind=link.relation_kind,
                    confidence=link.confidence,
                )
            )
        db.flush()


class EvidenceRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: EvidenceService | None = None,
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
            raise ValueError("evidence worker timing settings are invalid")

        self.session_factory = session_factory
        self.service = service or EvidenceService()
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
                        pipeline=StoryPipeline.EVIDENCE_ANALYSIS.value,
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

    def _record_failure(
        self,
        db: Session,
        *,
        claim: StoryProcessingClaim,
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
                    failure_time
                    + timedelta(seconds=delay)
                ),
                error_code=type(exc).__name__,
                error_message=str(exc)[:2000],
            )
        except StoryProcessingLeaseLostError:
            self.processing_repository.mark_lease_lost(
                db,
                run_id=claim.run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired while handling evidence failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> EvidenceBatchResult:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        processed = 0
        skipped = 0
        failed = 0

        with self.session_factory() as db:
            claim_now = self.clock()

            with db.begin():
                stale_story_ids = (
                    self.service.repository.deactivate_without_active_groups(
                        db,
                        now=claim_now,
                    )
                )
                if stale_story_ids:
                    self.processing_repository.invalidate_processed(
                        db,
                        pipeline=StoryPipeline.EVIDENCE_ANALYSIS.value,
                        story_ids=stale_story_ids,
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
                                reason=(
                                    "story no longer has a complete active "
                                    "claim-group generation"
                                ),
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
                                reason=(
                                    "story evidence identity changed "
                                    "before provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = self.service.prepare(snapshot)

                except StoryProcessingLeaseLostError:
                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=claim.run_id,
                            now=self.clock(),
                            error_message=(
                                "processing lease was lost "
                                "before evidence provider execution"
                            ),
                        )
                    skipped += 1
                    continue

                assert prepared is not None

                try:
                    result = self.service.run_provider(prepared)
                except Exception as exc:
                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=self.clock(),
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Evidence analysis failed",
                        extra={
                            "story_id": str(claim.story_id),
                            "processing_run_id": str(claim.run_id),
                        },
                    )
                    continue

                try:
                    with db.begin():
                        now = self.clock()

                        self.story_repository.acquire_processing_coordination_lock(
                            db
                        )

                        heartbeat_ok = self.processing_repository.heartbeat(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=now,
                            claim_expires_at=(
                                now
                                + timedelta(
                                    seconds=self.claim_ttl_seconds
                                )
                            ),
                        )
                        if not heartbeat_ok:
                            raise StoryProcessingLeaseLostError(
                                "processing lease was lost before finalization"
                            )

                        story = self.service.claim_repository.get_story(
                            db,
                            story_id=claim.story_id,
                        )
                        if story is None:
                            self.processing_repository.skip(
                                db,
                                state_id=claim.state_id,
                                run_id=claim.run_id,
                                worker_id=self.worker_id,
                                now=now,
                                reason=(
                                    "story became inactive "
                                    "during evidence analysis"
                                ),
                            )
                            skipped += 1
                            continue

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
                                now=now,
                                reason=(
                                    "story no longer has a complete active "
                                    "claim-group generation"
                                ),
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
                                now=now,
                                reason=(
                                    "story evidence identity changed "
                                    "during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        self.service.persist_result(
                            db,
                            snapshot,
                            prepared=prepared,
                            result=result,
                            processing_run_id=claim.run_id,
                            analyzed_at=now,
                        )
                        self.processing_repository.complete(
                            db,
                            state_id=claim.state_id,
                            run_id=claim.run_id,
                            worker_id=self.worker_id,
                            now=now,
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
                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=self.clock(),
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Evidence finalization failed",
                        extra={
                            "story_id": str(claim.story_id),
                            "processing_run_id": str(claim.run_id),
                        },
                    )

        return EvidenceBatchResult(
            selected=len(claimed),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
