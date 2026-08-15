from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)


class ArticleProcessingLeaseLostError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ArticleProcessingCandidate:
    article_id: UUID
    input_hash: str
    provider: str
    provider_version: str
    configuration_version: str


@dataclass(frozen=True, slots=True)
class ArticleProcessingClaim:
    article_id: UUID
    state_id: UUID
    run_id: UUID
    attempt_number: int


class ArticleProcessingRepository:
    def ensure_state(
        self,
        db: Session,
        *,
        article_id: UUID,
        pipeline: str,
    ) -> ArticleProcessingState:
        state = db.scalar(
            select(ArticleProcessingState).where(
                ArticleProcessingState.article_id == article_id,
                ArticleProcessingState.pipeline == pipeline,
                ArticleProcessingState.deleted_at.is_(None),
            )
        )

        if state is not None:
            return state

        state_id = db.scalar(
            insert(ArticleProcessingState)
            .values(
                article_id=article_id,
                pipeline=pipeline,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ArticleProcessingState.article_id,
                    ArticleProcessingState.pipeline,
                ],
                index_where=ArticleProcessingState.deleted_at.is_(None),
            )
            .returning(ArticleProcessingState.id)
        )

        if state_id is not None:
            state = db.get(
                ArticleProcessingState,
                state_id,
            )
        else:
            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_id,
                    ArticleProcessingState.pipeline == pipeline,
                    ArticleProcessingState.deleted_at.is_(None),
                )
            )

        if state is None:
            raise RuntimeError(
                "article processing state upsert did not resolve"
            )

        return state

    def claim_candidates(
        self,
        db: Session,
        *,
        pipeline: str,
        candidates: list[ArticleProcessingCandidate],
        worker_id: str,
        now: datetime,
        claim_expires_at: datetime,
        limit: int,
    ) -> list[ArticleProcessingClaim]:
        if limit <= 0 or not candidates:
            return []

        if claim_expires_at <= now:
            raise ValueError(
                "claim_expires_at must be later than now"
            )

        candidates_by_article_id: dict[
            UUID,
            ArticleProcessingCandidate,
        ] = {}

        for candidate in candidates:
            if candidate.article_id in candidates_by_article_id:
                raise ValueError(
                    f"duplicate article candidate: {candidate.article_id}"
                )

            candidates_by_article_id[candidate.article_id] = candidate

            self.ensure_state(
                db,
                article_id=candidate.article_id,
                pipeline=pipeline,
            )

        pending_identity_conditions = [
            and_(
                ArticleProcessingState.article_id == candidate.article_id,
                or_(
                    ArticleProcessingState.processed_input_hash.is_distinct_from(
                        candidate.input_hash
                    ),
                    ArticleProcessingState.processed_provider.is_distinct_from(
                        candidate.provider
                    ),
                    ArticleProcessingState.processed_provider_version.is_distinct_from(
                        candidate.provider_version
                    ),
                    ArticleProcessingState.processed_configuration_version.is_distinct_from(
                        candidate.configuration_version
                    ),
                ),
            )
            for candidate in candidates
        ]

        states = list(
            db.scalars(
                select(ArticleProcessingState)
                .where(
                    ArticleProcessingState.pipeline == pipeline,
                    ArticleProcessingState.deleted_at.is_(None),
                    or_(
                        ArticleProcessingState.retry_after.is_(None),
                        ArticleProcessingState.retry_after <= now,
                    ),
                    or_(
                        ArticleProcessingState.claim_expires_at.is_(None),
                        ArticleProcessingState.claim_expires_at <= now,
                    ),
                    or_(*pending_identity_conditions),
                )
                .order_by(
                    ArticleProcessingState.created_at,
                    ArticleProcessingState.id,
                )
                .limit(limit)
                .with_for_update(
                    skip_locked=True,
                    of=ArticleProcessingState,
                )
                .execution_options(
                    populate_existing=True
                )
            ).all()
        )

        claims: list[ArticleProcessingClaim] = []

        for state in states:
            candidate = candidates_by_article_id[state.article_id]

            if (
                state.claim_expires_at is not None
                and state.claim_expires_at <= now
            ):
                db.execute(
                    update(ArticleProcessingRun)
                    .where(
                        ArticleProcessingRun.processing_state_id == state.id,
                        ArticleProcessingRun.attempt_number
                        == state.attempt_count,
                        ArticleProcessingRun.finished_at.is_(None),
                    )
                    .values(
                        finished_at=now,
                        outcome="lease_lost",
                        error_code="lease_lost",
                        error_message=(
                            "processing lease expired and was reclaimed"
                        ),
                    )
                )

            state.claimed_input_hash = candidate.input_hash
            state.claimed_provider = candidate.provider
            state.claimed_provider_version = candidate.provider_version
            state.claimed_configuration_version = (
                candidate.configuration_version
            )

            state.claimed_at = now
            state.claimed_by = worker_id
            state.claim_expires_at = claim_expires_at
            state.last_started_at = now
            state.attempt_count += 1

            run = ArticleProcessingRun(
                article_id=state.article_id,
                processing_state_id=state.id,
                pipeline=state.pipeline,
                input_hash=candidate.input_hash,
                provider=candidate.provider,
                provider_version=candidate.provider_version,
                configuration_version=(
                    candidate.configuration_version
                ),
                worker_id=worker_id,
                attempt_number=state.attempt_count,
                started_at=now,
            )

            db.add(run)
            db.flush()

            claims.append(
                ArticleProcessingClaim(
                    article_id=state.article_id,
                    state_id=state.id,
                    run_id=run.id,
                    attempt_number=state.attempt_count,
                )
            )

        return claims

    def heartbeat(
        self,
        db: Session,
        *,
        state_id: UUID,
        run_id: UUID,
        worker_id: str,
        now: datetime,
        claim_expires_at: datetime,
    ) -> bool:
        if claim_expires_at <= now:
            raise ValueError(
                "claim_expires_at must be later than now"
            )

        run = db.get(
            ArticleProcessingRun,
            run_id,
        )

        if (
            run is None
            or run.processing_state_id != state_id
            or run.worker_id != worker_id
            or run.finished_at is not None
        ):
            return False

        result = db.execute(
            update(ArticleProcessingState)
            .where(
                ArticleProcessingState.id == state_id,
                ArticleProcessingState.deleted_at.is_(None),
                ArticleProcessingState.claimed_by == worker_id,
                ArticleProcessingState.claim_expires_at > now,
                ArticleProcessingState.attempt_count
                == run.attempt_number,
                ArticleProcessingState.claimed_input_hash
                == run.input_hash,
                ArticleProcessingState.claimed_provider
                == run.provider,
                ArticleProcessingState.claimed_provider_version
                == run.provider_version,
                ArticleProcessingState.claimed_configuration_version
                == run.configuration_version,
            )
            .values(
                claim_expires_at=claim_expires_at,
            )
        )

        return result.rowcount == 1

    def complete(
        self,
        db: Session,
        *,
        state_id: UUID,
        run_id: UUID,
        worker_id: str,
        now: datetime,
    ) -> None:
        state = self._get_locked_state(
            db,
            state_id=state_id,
        )

        self._assert_valid_lease(
            state=state,
            worker_id=worker_id,
            now=now,
        )

        run = self._get_matching_active_run(
            db,
            state=state,
            run_id=run_id,
            worker_id=worker_id,
        )

        state.processed_input_hash = state.claimed_input_hash
        state.processed_provider = state.claimed_provider
        state.processed_provider_version = (
            state.claimed_provider_version
        )
        state.processed_configuration_version = (
            state.claimed_configuration_version
        )
        state.last_processed_at = now

        self._release_claim(state)
        self._clear_error(state)

        run.finished_at = now
        run.outcome = "succeeded"
        run.error_code = None
        run.error_message = None

    def skip(
        self,
        db: Session,
        *,
        state_id: UUID,
        run_id: UUID,
        worker_id: str,
        now: datetime,
        reason: str,
    ) -> None:
        state = self._get_locked_state(
            db,
            state_id=state_id,
        )

        self._assert_valid_lease(
            state=state,
            worker_id=worker_id,
            now=now,
        )

        run = self._get_matching_active_run(
            db,
            state=state,
            run_id=run_id,
            worker_id=worker_id,
        )

        self._release_claim(state)
        self._clear_error(state)

        run.finished_at = now
        run.outcome = "skipped"
        run.error_code = "skipped"
        run.error_message = reason[:2000]

    def fail(
        self,
        db: Session,
        *,
        state_id: UUID,
        run_id: UUID,
        worker_id: str,
        now: datetime,
        retry_after: datetime | None,
        error_code: str,
        error_message: str,
    ) -> None:
        state = self._get_locked_state(
            db,
            state_id=state_id,
        )

        self._assert_valid_lease(
            state=state,
            worker_id=worker_id,
            now=now,
        )

        run = self._get_matching_active_run(
            db,
            state=state,
            run_id=run_id,
            worker_id=worker_id,
        )

        self._release_claim(state)

        state.retry_after = retry_after
        state.last_error_code = error_code
        state.last_error_message = error_message
        state.last_error_at = now

        run.finished_at = now
        run.outcome = "failed"
        run.error_code = error_code
        run.error_message = error_message

    def invalidate_processed(
        self,
        db: Session,
        *,
        pipeline: str,
        article_ids: list[UUID],
    ) -> int:
        if not article_ids:
            return 0

        result = db.execute(
            update(ArticleProcessingState)
            .where(
                ArticleProcessingState.pipeline == pipeline,
                ArticleProcessingState.article_id.in_(article_ids),
                ArticleProcessingState.deleted_at.is_(None),
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

    def mark_lease_lost(
        self,
        db: Session,
        *,
        run_id: UUID,
        now: datetime,
        error_message: str | None = None,
    ) -> None:
        run = db.get(
            ArticleProcessingRun,
            run_id,
        )

        if (
            run is None
            or run.finished_at is not None
        ):
            return

        run.finished_at = now
        run.outcome = "lease_lost"
        run.error_code = "lease_lost"
        run.error_message = error_message

    @staticmethod
    def _get_locked_state(
        db: Session,
        *,
        state_id: UUID,
    ) -> ArticleProcessingState:
        state = db.scalar(
            select(ArticleProcessingState)
            .where(
                ArticleProcessingState.id == state_id,
                ArticleProcessingState.deleted_at.is_(None),
            )
            .with_for_update(
                of=ArticleProcessingState
            )
            .execution_options(
                populate_existing=True
            )
        )

        if state is None:
            raise ArticleProcessingLeaseLostError(
                "processing state no longer exists"
            )

        return state

    @staticmethod
    def _get_matching_active_run(
        db: Session,
        *,
        state: ArticleProcessingState,
        run_id: UUID,
        worker_id: str,
    ) -> ArticleProcessingRun:
        run = db.get(
            ArticleProcessingRun,
            run_id,
        )

        if (
            run is None
            or run.processing_state_id != state.id
            or run.article_id != state.article_id
            or run.pipeline != state.pipeline
            or run.worker_id != worker_id
            or run.finished_at is not None
            or run.attempt_number != state.attempt_count
            or run.input_hash != state.claimed_input_hash
            or run.provider != state.claimed_provider
            or run.provider_version
            != state.claimed_provider_version
            or run.configuration_version
            != state.claimed_configuration_version
        ):
            raise ArticleProcessingLeaseLostError(
                "processing run does not match active lease"
            )

        return run

    @staticmethod
    def _release_claim(
        state: ArticleProcessingState,
    ) -> None:
        state.claimed_input_hash = None
        state.claimed_provider = None
        state.claimed_provider_version = None
        state.claimed_configuration_version = None

        state.claimed_at = None
        state.claimed_by = None
        state.claim_expires_at = None

    @staticmethod
    def _clear_error(
        state: ArticleProcessingState,
    ) -> None:
        state.retry_after = None
        state.last_error_code = None
        state.last_error_message = None
        state.last_error_at = None

    @staticmethod
    def _assert_valid_lease(
        *,
        state: ArticleProcessingState,
        worker_id: str,
        now: datetime,
    ) -> None:
        if (
            state.claimed_by != worker_id
            or state.claimed_at is None
            or state.claim_expires_at is None
            or state.claim_expires_at <= now
        ):
            raise ArticleProcessingLeaseLostError(
                "processing lease is no longer valid"
            )