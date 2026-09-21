from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.story_processing import StoryProcessingRun, StoryProcessingState


class StoryProcessingLeaseLostError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoryProcessingCandidate:
    story_id: UUID
    input_hash: str
    provider: str
    provider_version: str
    configuration_version: str


@dataclass(frozen=True, slots=True)
class StoryProcessingClaim:
    story_id: UUID
    input_hash: str
    provider: str
    provider_version: str
    configuration_version: str
    state_id: UUID
    run_id: UUID
    attempt_number: int

    def matches_candidate(self, candidate: StoryProcessingCandidate) -> bool:
        return (
            self.story_id == candidate.story_id
            and self.input_hash == candidate.input_hash
            and self.provider == candidate.provider
            and self.provider_version == candidate.provider_version
            and self.configuration_version == candidate.configuration_version
        )


class StoryProcessingRepository:
    def ensure_state(self, db: Session, *, story_id: UUID, pipeline: str) -> StoryProcessingState:
        state = db.scalar(
            select(StoryProcessingState).where(
                StoryProcessingState.story_id == story_id,
                StoryProcessingState.pipeline == pipeline,
                StoryProcessingState.deleted_at.is_(None),
            )
        )
        if state is not None:
            return state

        state_id = db.scalar(
            insert(StoryProcessingState)
            .values(story_id=story_id, pipeline=pipeline)
            .on_conflict_do_nothing(
                index_elements=[StoryProcessingState.story_id, StoryProcessingState.pipeline],
                index_where=StoryProcessingState.deleted_at.is_(None),
            )
            .returning(StoryProcessingState.id)
        )
        state = (
            db.get(StoryProcessingState, state_id)
            if state_id is not None
            else db.scalar(
                select(StoryProcessingState).where(
                    StoryProcessingState.story_id == story_id,
                    StoryProcessingState.pipeline == pipeline,
                    StoryProcessingState.deleted_at.is_(None),
                )
            )
        )
        if state is None:
            raise RuntimeError("story processing state upsert did not resolve")
        return state

    def claim_candidates(
        self,
        db: Session,
        *,
        pipeline: str,
        candidates: list[StoryProcessingCandidate],
        worker_id: str,
        now: datetime,
        claim_expires_at: datetime,
        limit: int,
    ) -> list[StoryProcessingClaim]:
        if limit <= 0 or not candidates:
            return []
        if claim_expires_at <= now:
            raise ValueError("claim_expires_at must be later than now")

        by_story: dict[UUID, StoryProcessingCandidate] = {}
        for candidate in candidates:
            if candidate.story_id in by_story:
                raise ValueError(f"duplicate story candidate: {candidate.story_id}")
            by_story[candidate.story_id] = candidate
            self.ensure_state(db, story_id=candidate.story_id, pipeline=pipeline)

        pending = [
            and_(
                StoryProcessingState.story_id == candidate.story_id,
                or_(
                    StoryProcessingState.processed_input_hash.is_distinct_from(candidate.input_hash),
                    StoryProcessingState.processed_provider.is_distinct_from(candidate.provider),
                    StoryProcessingState.processed_provider_version.is_distinct_from(candidate.provider_version),
                    StoryProcessingState.processed_configuration_version.is_distinct_from(candidate.configuration_version),
                ),
            )
            for candidate in candidates
        ]

        states = list(
            db.scalars(
                select(StoryProcessingState)
                .where(
                    StoryProcessingState.pipeline == pipeline,
                    StoryProcessingState.deleted_at.is_(None),
                    or_(StoryProcessingState.retry_after.is_(None), StoryProcessingState.retry_after <= now),
                    or_(StoryProcessingState.claim_expires_at.is_(None), StoryProcessingState.claim_expires_at <= now),
                    or_(*pending),
                )
                .order_by(StoryProcessingState.created_at, StoryProcessingState.id)
                .limit(limit)
                .with_for_update(skip_locked=True, of=StoryProcessingState)
                .execution_options(populate_existing=True)
            ).all()
        )

        claims: list[StoryProcessingClaim] = []
        for state in states:
            candidate = by_story[state.story_id]
            if state.claim_expires_at is not None and state.claim_expires_at <= now:
                db.execute(
                    update(StoryProcessingRun)
                    .where(
                        StoryProcessingRun.processing_state_id == state.id,
                        StoryProcessingRun.attempt_number == state.attempt_count,
                        StoryProcessingRun.finished_at.is_(None),
                    )
                    .values(
                        finished_at=now,
                        outcome="lease_lost",
                        error_code="lease_lost",
                        error_message="processing lease expired and was reclaimed",
                    )
                )

            state.claimed_input_hash = candidate.input_hash
            state.claimed_provider = candidate.provider
            state.claimed_provider_version = candidate.provider_version
            state.claimed_configuration_version = candidate.configuration_version
            state.claimed_at = now
            state.claimed_by = worker_id
            state.claim_expires_at = claim_expires_at
            state.last_started_at = now
            state.attempt_count += 1

            run = StoryProcessingRun(
                story_id=state.story_id,
                processing_state_id=state.id,
                pipeline=state.pipeline,
                input_hash=candidate.input_hash,
                provider=candidate.provider,
                provider_version=candidate.provider_version,
                configuration_version=candidate.configuration_version,
                worker_id=worker_id,
                attempt_number=state.attempt_count,
                started_at=now,
            )
            db.add(run)
            db.flush()
            claims.append(
                StoryProcessingClaim(
                    story_id=state.story_id,
                    input_hash=candidate.input_hash,
                    provider=candidate.provider,
                    provider_version=candidate.provider_version,
                    configuration_version=candidate.configuration_version,
                    state_id=state.id,
                    run_id=run.id,
                    attempt_number=state.attempt_count,
                )
            )
        return claims

    def heartbeat(self, db: Session, *, state_id: UUID, run_id: UUID, worker_id: str, now: datetime, claim_expires_at: datetime) -> bool:
        if claim_expires_at <= now:
            raise ValueError("claim_expires_at must be later than now")
        run = db.get(StoryProcessingRun, run_id)
        if run is None or run.processing_state_id != state_id or run.worker_id != worker_id or run.finished_at is not None:
            return False
        result = db.execute(
            update(StoryProcessingState)
            .where(
                StoryProcessingState.id == state_id,
                StoryProcessingState.story_id == run.story_id,
                StoryProcessingState.pipeline == run.pipeline,
                StoryProcessingState.deleted_at.is_(None),
                StoryProcessingState.claimed_by == worker_id,
                StoryProcessingState.claim_expires_at > now,
                StoryProcessingState.attempt_count == run.attempt_number,
                StoryProcessingState.claimed_input_hash == run.input_hash,
                StoryProcessingState.claimed_provider == run.provider,
                StoryProcessingState.claimed_provider_version == run.provider_version,
                StoryProcessingState.claimed_configuration_version == run.configuration_version,
            )
            .values(claim_expires_at=claim_expires_at)
        )
        return result.rowcount == 1

    def complete(self, db: Session, *, state_id: UUID, run_id: UUID, worker_id: str, now: datetime) -> None:
        state = self._get_locked_state(db, state_id=state_id)
        self._assert_valid_lease(state=state, worker_id=worker_id, now=now)
        run = self._get_matching_active_run(db, state=state, run_id=run_id, worker_id=worker_id)
        state.processed_input_hash = state.claimed_input_hash
        state.processed_provider = state.claimed_provider
        state.processed_provider_version = state.claimed_provider_version
        state.processed_configuration_version = state.claimed_configuration_version
        state.last_processed_at = now
        self._release_claim(state)
        self._clear_error(state)
        run.finished_at = now
        run.outcome = "succeeded"
        run.error_code = None
        run.error_message = None

    def skip(self, db: Session, *, state_id: UUID, run_id: UUID, worker_id: str, now: datetime, reason: str) -> None:
        state = self._get_locked_state(db, state_id=state_id)
        self._assert_valid_lease(state=state, worker_id=worker_id, now=now)
        run = self._get_matching_active_run(db, state=state, run_id=run_id, worker_id=worker_id)
        self._release_claim(state)
        self._clear_error(state)
        run.finished_at = now
        run.outcome = "skipped"
        run.error_code = "skipped"
        run.error_message = reason[:2000]

    def fail(self, db: Session, *, state_id: UUID, run_id: UUID, worker_id: str, now: datetime, retry_after: datetime | None, error_code: str, error_message: str) -> None:
        state = self._get_locked_state(db, state_id=state_id)
        self._assert_valid_lease(state=state, worker_id=worker_id, now=now)
        run = self._get_matching_active_run(db, state=state, run_id=run_id, worker_id=worker_id)
        self._release_claim(state)
        state.retry_after = retry_after
        state.last_error_code = error_code
        state.last_error_message = error_message
        state.last_error_at = now
        run.finished_at = now
        run.outcome = "failed"
        run.error_code = error_code
        run.error_message = error_message

    def invalidate_processed(self, db: Session, *, pipeline: str, story_ids: list[UUID]) -> int:
        if not story_ids:
            return 0
        result = db.execute(
            update(StoryProcessingState)
            .where(
                StoryProcessingState.pipeline == pipeline,
                StoryProcessingState.story_id.in_(story_ids),
                StoryProcessingState.deleted_at.is_(None),
            )
            .values(
                processed_input_hash=None,
                processed_provider=None,
                processed_provider_version=None,
                processed_configuration_version=None,
                last_processed_at=None,
            )
        )
        return result.rowcount or 0

    def mark_lease_lost(self, db: Session, *, run_id: UUID, now: datetime, error_message: str | None = None) -> None:
        run = db.get(StoryProcessingRun, run_id)
        if run is None or run.finished_at is not None:
            return
        run.finished_at = now
        run.outcome = "lease_lost"
        run.error_code = "lease_lost"
        run.error_message = error_message

    @staticmethod
    def _get_locked_state(db: Session, *, state_id: UUID) -> StoryProcessingState:
        state = db.scalar(
            select(StoryProcessingState)
            .where(StoryProcessingState.id == state_id, StoryProcessingState.deleted_at.is_(None))
            .with_for_update(of=StoryProcessingState)
            .execution_options(populate_existing=True)
        )
        if state is None:
            raise StoryProcessingLeaseLostError("processing state no longer exists")
        return state

    @staticmethod
    def _assert_valid_lease(*, state: StoryProcessingState, worker_id: str, now: datetime) -> None:
        if (
            state.claimed_by != worker_id
            or state.claimed_at is None
            or state.claim_expires_at is None
            or state.claim_expires_at <= now
        ):
            raise StoryProcessingLeaseLostError("processing lease is no longer valid")

    @staticmethod
    def _get_matching_active_run(db: Session, *, state: StoryProcessingState, run_id: UUID, worker_id: str) -> StoryProcessingRun:
        run = db.get(StoryProcessingRun, run_id)
        if (
            run is None
            or run.processing_state_id != state.id
            or run.story_id != state.story_id
            or run.pipeline != state.pipeline
            or run.worker_id != worker_id
            or run.attempt_number != state.attempt_count
            or run.finished_at is not None
            or run.input_hash != state.claimed_input_hash
            or run.provider != state.claimed_provider
            or run.provider_version != state.claimed_provider_version
            or run.configuration_version != state.claimed_configuration_version
        ):
            raise StoryProcessingLeaseLostError("processing run no longer matches the active lease")
        return run

    @staticmethod
    def _release_claim(state: StoryProcessingState) -> None:
        state.claimed_input_hash = None
        state.claimed_provider = None
        state.claimed_provider_version = None
        state.claimed_configuration_version = None
        state.claimed_at = None
        state.claimed_by = None
        state.claim_expires_at = None

    @staticmethod
    def _clear_error(state: StoryProcessingState) -> None:
        state.retry_after = None
        state.last_error_code = None
        state.last_error_message = None
        state.last_error_at = None
