import hashlib
import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
    ClaimRelationAnalyzer,
    ClaimRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimAnalysisResult,
    StoryClaimInput,
)
from app.claim_relations.rule_based import RuleBasedClaimRelationAnalyzer
from app.enums.story_pipeline import StoryPipeline
from app.models.claim import ArticleClaim
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimGroupMember,
    StoryClaimRelation,
)
from app.models.story import Story
from app.models.story_processing import StoryProcessingRun
from app.repositories.claim_relation import (
    ClaimRelationRepository,
    EligibleStoryMembership,
)
from app.repositories.story import StoryRepository
from app.repositories.story_processing import (
    StoryProcessingCandidate,
    StoryProcessingClaim,
    StoryProcessingLeaseLostError,
    StoryProcessingRepository,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClaimRelationBatchResult:
    selected: int
    processed: int
    skipped: int
    failed: int


@dataclass(frozen=True, slots=True)
class PreparedClaimRelationAnalysis:
    story_id: UUID
    language_code: str | None
    expected_hash: str
    analysis_input: StoryClaimAnalysisInput


@dataclass(frozen=True, slots=True)
class StoryClaimSnapshot:
    story: Story
    memberships: tuple[EligibleStoryMembership, ...]
    claims: tuple[ArticleClaim, ...]


class ClaimRelationService:
    CONFIG_VERSION = "1"

    def __init__(
        self,
        analyzer: ClaimRelationAnalyzer | None = None,
        repository: ClaimRelationRepository | None = None,
        *,
        config_version: str = CONFIG_VERSION,
    ) -> None:
        self.analyzer = analyzer or RuleBasedClaimRelationAnalyzer()
        self.repository = repository or ClaimRelationRepository()
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
    ) -> StoryClaimSnapshot | None:
        story = self.repository.get_story(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if story is None:
            return None

        memberships = self.repository.load_eligible_memberships(
            db,
            story_id=story_id,
            for_update=for_update,
        )
        if not memberships:
            return None

        article_ids = [item.article.id for item in memberships]
        if lock_articles:
            self.repository.lock_articles(
                db,
                article_ids=article_ids,
            )
            memberships = self.repository.load_eligible_memberships(
                db,
                story_id=story_id,
                for_update=for_update,
            )
            article_ids = [item.article.id for item in memberships]
            if not article_ids:
                return None

        claims = self.repository.load_active_claims(
            db,
            article_ids=article_ids,
            for_update=for_update,
        )
        if not claims:
            return None

        eligible_ids = set(article_ids)
        if any(claim.article_id not in eligible_ids for claim in claims):
            raise ValueError("claim snapshot contains an ineligible article")

        return StoryClaimSnapshot(
            story=story,
            memberships=tuple(memberships),
            claims=tuple(claims),
        )

    def analysis_hash(
        self,
        snapshot: StoryClaimSnapshot,
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
        claim_identity = [
            [
                str(claim.id),
                str(claim.processing_run_id),
                str(claim.article_id),
                claim.claim_hash,
                claim.normalized_claim,
                claim.text_source.value,
                claim.start_offset,
                claim.end_offset,
                claim.sentence_index,
                claim.confidence,
                claim.extraction_provider,
                claim.extraction_version,
                claim.semantic_model or "",
                claim.semantic_input_hash or "",
            ]
            for claim in sorted(
                snapshot.claims,
                key=lambda value: (
                    str(value.article_id),
                    value.text_source.value,
                    value.sentence_index,
                    value.start_offset,
                    str(value.id),
                ),
            )
        ]
        payload = [
            str(snapshot.story.id),
            snapshot.story.language_code or "",
            membership_identity,
            claim_identity,
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
        snapshot: StoryClaimSnapshot,
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
        snapshot: StoryClaimSnapshot,
    ) -> PreparedClaimRelationAnalysis:
        source_by_article = {
            item.article.id: item.source_id
            for item in snapshot.memberships
        }
        claims = tuple(
            StoryClaimInput(
                claim_id=claim.id,
                article_id=claim.article_id,
                source_id=source_by_article[claim.article_id],
                claim_text=claim.claim_text,
                normalized_claim=claim.normalized_claim,
                claim_hash=claim.claim_hash,
                confidence=claim.confidence,
                semantic_embedding=(
                    tuple(claim.semantic_embedding)
                    if claim.semantic_embedding
                    else None
                ),
                semantic_model=claim.semantic_model,
            )
            for claim in sorted(
                snapshot.claims,
                key=lambda value: (
                    value.normalized_claim,
                    str(value.article_id),
                    str(value.id),
                ),
            )
        )
        candidate = self.candidate(snapshot)
        return PreparedClaimRelationAnalysis(
            story_id=snapshot.story.id,
            language_code=snapshot.story.language_code,
            expected_hash=candidate.input_hash,
            analysis_input=StoryClaimAnalysisInput(
                story_id=snapshot.story.id,
                language_code=snapshot.story.language_code,
                claims=claims,
            ),
        )

    @staticmethod
    def _validate_result(
        *,
        prepared: PreparedClaimRelationAnalysis,
        result: StoryClaimAnalysisResult,
    ) -> None:
        claim_ids = {
            claim.claim_id
            for claim in prepared.analysis_input.claims
        }
        seen_claims: set[UUID] = set()
        groups_by_key = {}

        for group in result.groups:
            if not group.key.strip():
                raise ValueError("claim group key must not be empty")
            if group.key in groups_by_key:
                raise ValueError("duplicate claim group key")
            if (
                not math.isfinite(group.confidence)
                or not 0 <= group.confidence <= 1
            ):
                raise ValueError(
                    "claim group confidence must be between zero and one"
                )
            if not group.members:
                raise ValueError(
                    "claim group must contain at least one member"
                )

            member_ids: set[UUID] = set()
            for member in group.members:
                if member.claim_id not in claim_ids:
                    raise ValueError(
                        "claim group references an unknown claim"
                    )
                if member.claim_id in member_ids:
                    raise ValueError(
                        "claim appears twice in one claim group"
                    )
                if member.claim_id in seen_claims:
                    raise ValueError(
                        "claim appears in more than one claim group"
                    )
                if not isinstance(
                    member.match_kind,
                    ClaimGroupMatchKind,
                ):
                    raise ValueError(
                        "claim group match kind is invalid"
                    )
                if (
                    not math.isfinite(member.similarity_score)
                    or not 0 <= member.similarity_score <= 1
                ):
                    raise ValueError(
                        "claim group member similarity must be between zero and one"
                    )
                member_ids.add(member.claim_id)
                seen_claims.add(member.claim_id)

            if group.representative_claim_id not in member_ids:
                raise ValueError(
                    "representative claim must belong to its group"
                )
            groups_by_key[group.key] = group

        if seen_claims != claim_ids:
            raise ValueError(
                "claim relation result must partition every input claim"
            )

        seen_relations: set[
            tuple[str, str, ClaimRelationKind]
        ] = set()

        for relation in result.relations:
            if not isinstance(
                relation.relation_kind,
                ClaimRelationKind,
            ):
                raise ValueError(
                    "claim relation kind is invalid"
                )
            if (
                relation.left_group_key not in groups_by_key
                or relation.right_group_key not in groups_by_key
            ):
                raise ValueError(
                    "claim relation references an unknown group"
                )
            if (
                relation.left_group_key
                == relation.right_group_key
            ):
                raise ValueError(
                    "claim relation cannot reference one group twice"
                )
            if (
                not math.isfinite(relation.confidence)
                or not 0 <= relation.confidence <= 1
            ):
                raise ValueError(
                    "claim relation confidence must be between zero and one"
                )

            left, right = sorted(
                (
                    relation.left_group_key,
                    relation.right_group_key,
                )
            )
            key = (
                left,
                right,
                relation.relation_kind,
            )
            if key in seen_relations:
                raise ValueError(
                    "duplicate claim relation"
                )
            seen_relations.add(key)

    def run_provider(
        self,
        prepared: PreparedClaimRelationAnalysis,
    ) -> StoryClaimAnalysisResult:
        result = self.analyzer.analyze(
            prepared.analysis_input
        )
        self._validate_result(
            prepared=prepared,
            result=result,
        )
        return result

    @staticmethod
    def _group_hash(
        claim_by_id: dict[UUID, ArticleClaim],
        claim_ids: list[UUID],
    ) -> str:
        payload = sorted(
            [
                claim_by_id[claim_id].claim_hash,
                claim_by_id[claim_id].normalized_claim,
            ]
            for claim_id in claim_ids
        )
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def persist_result(
        self,
        db: Session,
        snapshot: StoryClaimSnapshot,
        *,
        prepared: PreparedClaimRelationAnalysis,
        result: StoryClaimAnalysisResult,
        processing_run_id: UUID,
        analyzed_at: datetime,
    ) -> None:
        if snapshot.story.id != prepared.story_id:
            raise ValueError(
                "prepared claim relation analysis belongs to another story"
            )
        if self.analysis_hash(snapshot) != prepared.expected_hash:
            raise ValueError(
                "story claim input identity changed after preparation"
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
            or run.pipeline
            != StoryPipeline.CLAIM_RELATIONS.value
            or run.input_hash != prepared.expected_hash
            or run.provider != self.analyzer.provider
            or run.provider_version
            != self.analyzer.version
            or run.configuration_version
            != self.processing_configuration_version
        ):
            raise ValueError(
                "processing run does not match claim relation identity"
            )

        self._validate_result(
            prepared=prepared,
            result=result,
        )
        claim_by_id = {
            claim.id: claim
            for claim in snapshot.claims
        }

        self.repository.replace_story_results(
            db,
            story_id=snapshot.story.id,
            now=analyzed_at,
        )

        group_by_key: dict[
            str,
            StoryClaimGroup,
        ] = {}
        used_hashes: set[str] = set()

        for group_result in sorted(
            result.groups,
            key=lambda item: item.key,
        ):
            claim_ids = [
                member.claim_id
                for member in group_result.members
            ]
            group_hash = self._group_hash(
                claim_by_id,
                claim_ids,
            )
            if group_hash in used_hashes:
                raise ValueError(
                    "provider produced duplicate persisted claim groups"
                )
            used_hashes.add(group_hash)

            group = StoryClaimGroup(
                story_id=snapshot.story.id,
                processing_run_id=processing_run_id,
                representative_claim_id=(
                    group_result.representative_claim_id
                ),
                group_hash=group_hash,
                confidence=group_result.confidence,
                analysis_provider=(
                    self.analyzer.provider
                ),
                analysis_version=(
                    self.analyzer.version
                ),
                analyzed_at=analyzed_at,
            )
            db.add(group)
            db.flush()
            group_by_key[
                group_result.key
            ] = group

            for member in sorted(
                group_result.members,
                key=lambda item: str(
                    item.claim_id
                ),
            ):
                db.add(
                    StoryClaimGroupMember(
                        group_id=group.id,
                        claim_id=member.claim_id,
                        processing_run_id=(
                            processing_run_id
                        ),
                        similarity_score=(
                            member.similarity_score
                        ),
                        match_kind=(
                            member.match_kind
                        ),
                    )
                )

        db.flush()

        for relation in sorted(
            result.relations,
            key=lambda item: (
                min(
                    item.left_group_key,
                    item.right_group_key,
                ),
                max(
                    item.left_group_key,
                    item.right_group_key,
                ),
                item.relation_kind.value,
            ),
        ):
            left_key, right_key = sorted(
                (
                    relation.left_group_key,
                    relation.right_group_key,
                )
            )
            db.add(
                StoryClaimRelation(
                    story_id=snapshot.story.id,
                    processing_run_id=(
                        processing_run_id
                    ),
                    left_group_id=(
                        group_by_key[
                            left_key
                        ].id
                    ),
                    right_group_id=(
                        group_by_key[
                            right_key
                        ].id
                    ),
                    relation_kind=(
                        relation.relation_kind
                    ),
                    confidence=(
                        relation.confidence
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


class ClaimRelationRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: ClaimRelationService | None = None,
        processing_repository: (
            StoryProcessingRepository
            | None
        ) = None,
        story_repository: (
            StoryRepository
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
                "claim relation worker timing settings are invalid"
            )

        self.session_factory = session_factory
        self.service = (
            service
            or ClaimRelationService()
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
            or (
                lambda: datetime.now(
                    UTC
                )
            )
        )

    def _claim_pending(
        self,
        db: Session,
        *,
        limit: int,
        now: datetime,
    ) -> list[
        StoryProcessingClaim
    ]:
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
                self.service.repository.list_candidate_stories(
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

            candidates: list[
                StoryProcessingCandidate
            ] = []

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
                    self.processing_repository.claim_candidates(
                        db,
                        pipeline=(
                            StoryPipeline.CLAIM_RELATIONS
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
                            - len(claimed)
                        ),
                    )
                )

            last = stories[-1]
            last_created_at = (
                last.created_at
            )
            last_story_id = (
                last.id
            )

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
                error_code=(
                    type(exc).__name__
                ),
                error_message=(
                    str(exc)[:2000]
                ),
            )
        except StoryProcessingLeaseLostError:
            self.processing_repository.mark_lease_lost(
                db,
                run_id=claim.run_id,
                now=failure_time,
                error_message=(
                    "processing lease expired "
                    "while handling claim relation failure"
                ),
            )

    def run_pending(
        self,
        *,
        limit: int,
    ) -> ClaimRelationBatchResult:
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
                stale_story_ids = (
                    self.service.repository.deactivate_ineligible_results(
                        db,
                        now=claim_now,
                    )
                )
                if stale_story_ids:
                    self.processing_repository.invalidate_processed(
                        db,
                        pipeline=(
                            StoryPipeline.CLAIM_RELATIONS
                            .value
                        ),
                        story_ids=(
                            stale_story_ids
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
                        snapshot = (
                            self.service.load_snapshot(
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
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=self.clock(),
                                reason=(
                                    "story no longer has eligible claims"
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
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=self.clock(),
                                reason=(
                                    "story claim identity changed "
                                    "before provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        prepared = (
                            self.service.prepare(
                                snapshot
                            )
                        )

                except StoryProcessingLeaseLostError:
                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=(
                                claim.run_id
                            ),
                            now=self.clock(),
                            error_message=(
                                "processing lease was lost "
                                "before provider execution"
                            ),
                        )
                    skipped += 1
                    continue

                assert prepared is not None

                try:
                    result = (
                        self.service.run_provider(
                            prepared
                        )
                    )
                except Exception as exc:
                    with db.begin():
                        self._record_failure(
                            db,
                            claim=claim,
                            failure_time=(
                                self.clock()
                            ),
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Claim relation analysis failed",
                        extra={
                            "story_id": str(
                                claim.story_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                        },
                    )
                    continue

                try:
                    with db.begin():
                        now = self.clock()

                        self.story_repository.acquire_processing_coordination_lock(
                            db
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
                                now=now,
                                claim_expires_at=(
                                    now
                                    + timedelta(
                                        seconds=(
                                            self.claim_ttl_seconds
                                        )
                                    )
                                ),
                            )
                        )
                        if not heartbeat_ok:
                            raise StoryProcessingLeaseLostError(
                                "processing lease was lost before finalization"
                            )

                        story = (
                            self.service.repository.get_story(
                                db,
                                story_id=(
                                    claim.story_id
                                ),
                            )
                        )
                        if story is None:
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
                                    "story became inactive "
                                    "during provider execution"
                                ),
                            )
                            skipped += 1
                            continue

                        self.story_repository.acquire_clustering_lock(
                            db,
                            language_code=(
                                story.language_code
                            ),
                        )

                        snapshot = (
                            self.service.load_snapshot(
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
                                run_id=(
                                    claim.run_id
                                ),
                                worker_id=(
                                    self.worker_id
                                ),
                                now=now,
                                reason=(
                                    "story no longer has eligible claims"
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
                                now=now,
                                reason=(
                                    "story claim identity changed "
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
                            processing_run_id=(
                                claim.run_id
                            ),
                            analyzed_at=now,
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
                            now=now,
                        )

                    processed += 1

                except StoryProcessingLeaseLostError as exc:
                    db.rollback()
                    with db.begin():
                        self.processing_repository.mark_lease_lost(
                            db,
                            run_id=(
                                claim.run_id
                            ),
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
                            failure_time=(
                                self.clock()
                            ),
                            exc=exc,
                        )
                    failed += 1
                    logger.exception(
                        "Claim relation finalization failed",
                        extra={
                            "story_id": str(
                                claim.story_id
                            ),
                            "processing_run_id": str(
                                claim.run_id
                            ),
                        },
                    )

        return ClaimRelationBatchResult(
            selected=len(claimed),
            processed=processed,
            skipped=skipped,
            failed=failed,
        )
