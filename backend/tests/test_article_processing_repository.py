from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from tests.conftest import TestSessionLocal


PIPELINE = ArticlePipeline.ENTITY_TOPIC.value


def _create_articles(
    count: int,
) -> tuple[list[UUID], UUID]:
    token = uuid4().hex

    with TestSessionLocal.begin() as db:
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=f"https://{token}.test",
            source_type=SourceType.NEWS,
        )
        feed = Feed(
            source=source,
            name="Main",
            url=f"https://{token}.test/feed",
        )

        articles = [
            Article(
                feed=feed,
                identity_type=ArticleIdentityType.DERIVED,
                identity_key=f"{index:064x}",
            )
            for index in range(1, count + 1)
        ]

        db.add_all(articles)
        db.flush()

        return (
            [article.id for article in articles],
            source.id,
        )


def _cleanup_source(
    source_id: UUID,
) -> None:
    with TestSessionLocal.begin() as db:
        article_ids = (
            select(Article.id)
            .join(Feed)
            .where(
                Feed.source_id == source_id
            )
        )

        db.execute(
            delete(ArticleProcessingRun).where(
                ArticleProcessingRun.article_id.in_(
                    article_ids
                )
            )
        )

        db.execute(
            delete(Source).where(
                Source.id == source_id
            )
        )


def _candidate(
    article_id: UUID,
    suffix: str,
) -> ArticleProcessingCandidate:
    return ArticleProcessingCandidate(
        article_id=article_id,
        input_hash=(suffix * 64)[:64],
        provider="test-provider",
        provider_version="1",
        configuration_version="1",
    )


def _state_for(
    db,
    article_id: UUID,
) -> ArticleProcessingState:
    state = db.scalar(
        select(ArticleProcessingState).where(
            ArticleProcessingState.article_id == article_id,
            ArticleProcessingState.pipeline == PIPELINE,
            ArticleProcessingState.deleted_at.is_(None),
        )
    )

    assert state is not None
    return state


def test_ensure_state_is_idempotent():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    try:
        with TestSessionLocal.begin() as db:
            first = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=PIPELINE,
            )
            second = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=PIPELINE,
            )

            assert first.id == second.id

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id
                        == article_ids[0],
                        ArticleProcessingState.pipeline == PIPELINE,
                        ArticleProcessingState.deleted_at.is_(None),
                    )
                )
            )

            assert len(states) == 1

    finally:
        _cleanup_source(source_id)


def test_concurrent_ensure_state_creates_single_active_state():
    article_ids, source_id = _create_articles(1)
    barrier = Barrier(2)

    def ensure() -> UUID:
        repository = ArticleProcessingRepository()

        with TestSessionLocal.begin() as db:
            barrier.wait()

            return repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=PIPELINE,
            ).id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            state_ids = list(
                pool.map(
                    lambda _: ensure(),
                    range(2),
                )
            )

        assert state_ids[0] == state_ids[1]

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id
                        == article_ids[0],
                        ArticleProcessingState.pipeline == PIPELINE,
                        ArticleProcessingState.deleted_at.is_(None),
                    )
                )
            )

            assert len(states) == 1

    finally:
        _cleanup_source(source_id)


def test_claim_atomically_creates_state_lease_and_run():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    candidate = _candidate(article_ids[0], "a")
    now = datetime.now(UTC)

    try:
        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            assert len(claims) == 1

            claim = claims[0]

            assert claim.article_id == article_ids[0]
            assert claim.attempt_number == 1

            state = db.get(
                ArticleProcessingState,
                claim.state_id,
            )
            run = db.get(
                ArticleProcessingRun,
                claim.run_id,
            )

            assert state is not None
            assert run is not None

            assert state.article_id == article_ids[0]
            assert state.pipeline == PIPELINE
            assert state.claimed_by == "worker-1"
            assert state.claimed_at == now
            assert state.claim_expires_at == now + timedelta(minutes=5)
            assert state.claimed_input_hash == candidate.input_hash
            assert state.attempt_count == 1

            assert run.processing_state_id == state.id
            assert run.article_id == article_ids[0]
            assert run.pipeline == PIPELINE
            assert run.input_hash == candidate.input_hash
            assert run.provider == candidate.provider
            assert run.provider_version == candidate.provider_version
            assert (
                run.configuration_version
                == candidate.configuration_version
            )
            assert run.worker_id == "worker-1"
            assert run.attempt_number == 1
            assert run.started_at == now
            assert run.finished_at is None
            assert run.outcome is None

    finally:
        _cleanup_source(source_id)


def test_claim_transaction_rollback_removes_claim_and_run():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    candidate = _candidate(article_ids[0], "a")
    now = datetime.now(UTC)

    try:
        with TestSessionLocal() as db:
            transaction = db.begin()

            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            assert len(claims) == 1

            transaction.rollback()

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id
                        == article_ids[0],
                        ArticleProcessingState.pipeline == PIPELINE,
                    )
                )
            )
            runs = list(
                db.scalars(
                    select(ArticleProcessingRun).where(
                        ArticleProcessingRun.article_id
                        == article_ids[0],
                        ArticleProcessingRun.pipeline == PIPELINE,
                    )
                )
            )

            assert states == []
            assert runs == []

    finally:
        _cleanup_source(source_id)


def test_two_parallel_workers_claim_different_articles():
    article_ids, source_id = _create_articles(6)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    candidates = [
        _candidate(
            article_id,
            chr(97 + index),
        )
        for index, article_id in enumerate(article_ids)
    ]

    with TestSessionLocal.begin() as db:
        for article_id in article_ids:
            repository.ensure_state(
                db,
                article_id=article_id,
                pipeline=PIPELINE,
            )

    barrier = Barrier(2)

    def claim(worker_id: str):
        repo = ArticleProcessingRepository()

        with TestSessionLocal.begin() as db:
            barrier.wait()

            return repo.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=candidates,
                worker_id=worker_id,
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=3,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    claim,
                    ["worker-1", "worker-2"],
                )
            )

        first = {
            claim.article_id
            for claim in results[0]
        }
        second = {
            claim.article_id
            for claim in results[1]
        }

        assert len(first) == 3
        assert len(second) == 3
        assert first.isdisjoint(second)
        assert first | second == set(article_ids)

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id.in_(
                            article_ids
                        ),
                        ArticleProcessingState.pipeline == PIPELINE,
                    )
                )
            )
            runs = list(
                db.scalars(
                    select(ArticleProcessingRun).where(
                        ArticleProcessingRun.article_id.in_(
                            article_ids
                        ),
                        ArticleProcessingRun.pipeline == PIPELINE,
                    )
                )
            )

            assert len(states) == 6
            assert len(runs) == 6

            assert {
                state.article_id
                for state in states
            } == set(article_ids)

            assert {
                run.article_id
                for run in runs
            } == set(article_ids)

            assert all(
                state.attempt_count == 1
                for state in states
            )

            assert all(
                run.attempt_number == 1
                for run in runs
            )

    finally:
        _cleanup_source(source_id)


def test_claim_preserves_article_specific_identity():
    article_ids, source_id = _create_articles(2)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    first = _candidate(article_ids[0], "a")
    second = _candidate(article_ids[1], "b")

    try:
        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[first, second],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=2,
            )

            assert {
                claim.article_id
                for claim in claims
            } == set(article_ids)

        with TestSessionLocal() as db:
            states = {
                state.article_id: state
                for state in db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id.in_(
                            article_ids
                        )
                    )
                )
            }

            runs = {
                run.article_id: run
                for run in db.scalars(
                    select(ArticleProcessingRun).where(
                        ArticleProcessingRun.article_id.in_(
                            article_ids
                        )
                    )
                )
            }

            assert (
                states[article_ids[0]].claimed_input_hash
                == first.input_hash
            )
            assert (
                states[article_ids[1]].claimed_input_hash
                == second.input_hash
            )

            assert (
                runs[article_ids[0]].input_hash
                == first.input_hash
            )
            assert (
                runs[article_ids[1]].input_hash
                == second.input_hash
            )

    finally:
        _cleanup_source(source_id)


def test_processed_candidate_does_not_consume_limit():
    article_ids, source_id = _create_articles(2)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    first = _candidate(article_ids[0], "a")
    second = _candidate(article_ids[1], "b")

    try:
        with TestSessionLocal.begin() as db:
            state = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=PIPELINE,
            )

            repository.ensure_state(
                db,
                article_id=article_ids[1],
                pipeline=PIPELINE,
            )

            state.processed_input_hash = first.input_hash
            state.processed_provider = first.provider
            state.processed_provider_version = first.provider_version
            state.processed_configuration_version = (
                first.configuration_version
            )
            state.last_processed_at = now

        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[first, second],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            assert len(claims) == 1
            assert claims[0].article_id == article_ids[1]

    finally:
        _cleanup_source(source_id)


def test_heartbeat_extends_active_lease():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    try:
        with TestSessionLocal.begin() as db:
            claim = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "a")],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )[0]

            extended = now + timedelta(minutes=10)

            assert repository.heartbeat(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id="worker-1",
                now=now + timedelta(minutes=1),
                claim_expires_at=extended,
            )

            state = db.get(
                ArticleProcessingState,
                claim.state_id,
            )

            db.flush()
            db.refresh(state)

            assert state.claim_expires_at == extended

    finally:
        _cleanup_source(source_id)


def test_complete_promotes_identity_and_finishes_run():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    candidate = _candidate(article_ids[0], "a")
    now = datetime.now(UTC)
    finished_at = now + timedelta(seconds=10)

    try:
        with TestSessionLocal.begin() as db:
            claim = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )[0]

            repository.complete(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id="worker-1",
                now=finished_at,
            )

        with TestSessionLocal() as db:
            state = db.get(
                ArticleProcessingState,
                claim.state_id,
            )
            run = db.get(
                ArticleProcessingRun,
                claim.run_id,
            )

            assert state.processed_input_hash == candidate.input_hash
            assert state.processed_provider == candidate.provider
            assert (
                state.processed_provider_version
                == candidate.provider_version
            )
            assert (
                state.processed_configuration_version
                == candidate.configuration_version
            )
            assert state.last_processed_at == finished_at

            assert state.claimed_by is None
            assert state.claimed_at is None
            assert state.claim_expires_at is None
            assert state.claimed_input_hash is None

            assert run.finished_at == finished_at
            assert run.outcome == "succeeded"

    finally:
        _cleanup_source(source_id)


def test_skip_releases_claim_without_marking_processed():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    try:
        with TestSessionLocal.begin() as db:
            claim = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "a")],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )[0]

            repository.skip(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id="worker-1",
                now=now + timedelta(seconds=1),
                reason="article no longer eligible",
            )

        with TestSessionLocal() as db:
            state = db.get(
                ArticleProcessingState,
                claim.state_id,
            )
            run = db.get(
                ArticleProcessingRun,
                claim.run_id,
            )

            assert state.claimed_by is None
            assert state.claim_expires_at is None
            assert state.processed_input_hash is None

            assert run.outcome == "skipped"
            assert run.error_code == "skipped"
            assert (
                run.error_message
                == "article no longer eligible"
            )

    finally:
        _cleanup_source(source_id)


def test_failure_preserves_previous_successful_identity():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    previous_at = datetime.now(UTC) - timedelta(hours=1)
    now = datetime.now(UTC)

    previous = _candidate(article_ids[0], "a")
    current = _candidate(article_ids[0], "b")

    try:
        with TestSessionLocal.begin() as db:
            state = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=PIPELINE,
            )

            state.processed_input_hash = previous.input_hash
            state.processed_provider = previous.provider
            state.processed_provider_version = previous.provider_version
            state.processed_configuration_version = (
                previous.configuration_version
            )
            state.last_processed_at = previous_at

        with TestSessionLocal.begin() as db:
            claim = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[current],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )[0]

            retry_after = now + timedelta(minutes=15)

            repository.fail(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id="worker-1",
                now=now + timedelta(seconds=1),
                retry_after=retry_after,
                error_code="provider_error",
                error_message="provider failed",
            )

        with TestSessionLocal() as db:
            state = db.get(
                ArticleProcessingState,
                claim.state_id,
            )
            run = db.get(
                ArticleProcessingRun,
                claim.run_id,
            )

            assert state.processed_input_hash == previous.input_hash
            assert state.last_processed_at == previous_at
            assert state.retry_after == retry_after
            assert state.last_error_code == "provider_error"
            assert state.claimed_by is None

            assert run.outcome == "failed"
            assert run.error_code == "provider_error"

    finally:
        _cleanup_source(source_id)


def test_retry_after_blocks_claim_until_due():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    first_now = datetime.now(UTC)
    retry_after = first_now + timedelta(minutes=10)
    candidate = _candidate(article_ids[0], "a")

    try:
        with TestSessionLocal.begin() as db:
            claim = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-1",
                now=first_now,
                claim_expires_at=first_now + timedelta(minutes=5),
                limit=1,
            )[0]

            repository.fail(
                db,
                state_id=claim.state_id,
                run_id=claim.run_id,
                worker_id="worker-1",
                now=first_now + timedelta(seconds=1),
                retry_after=retry_after,
                error_code="failure",
                error_message="failure",
            )

        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-2",
                now=first_now + timedelta(minutes=5),
                claim_expires_at=first_now + timedelta(minutes=6),
                limit=1,
            )

            assert claims == []

        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-2",
                now=retry_after,
                claim_expires_at=retry_after + timedelta(minutes=5),
                limit=1,
            )

            assert len(claims) == 1
            assert claims[0].attempt_number == 2

    finally:
        _cleanup_source(source_id)


def test_expired_lease_reclaims_and_creates_next_attempt():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    first_now = datetime.now(UTC)
    second_now = first_now + timedelta(minutes=10)

    try:
        with TestSessionLocal.begin() as db:
            first = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "a")],
                worker_id="worker-1",
                now=first_now,
                claim_expires_at=first_now + timedelta(minutes=5),
                limit=1,
            )[0]

        with TestSessionLocal.begin() as db:
            second = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "b")],
                worker_id="worker-2",
                now=second_now,
                claim_expires_at=second_now + timedelta(minutes=5),
                limit=1,
            )[0]

            assert second.attempt_number == 2

        with TestSessionLocal() as db:
            first_run = db.get(
                ArticleProcessingRun,
                first.run_id,
            )
            second_run = db.get(
                ArticleProcessingRun,
                second.run_id,
            )
            state = db.get(
                ArticleProcessingState,
                second.state_id,
            )

            assert first_run.outcome == "lease_lost"
            assert first_run.finished_at == second_now
            assert first_run.error_code == "lease_lost"

            assert second_run.outcome is None
            assert second_run.finished_at is None
            assert second_run.attempt_number == 2

            assert state.attempt_count == 2
            assert state.claimed_by == "worker-2"

    finally:
        _cleanup_source(source_id)


def test_stale_worker_cannot_complete_after_reclaim():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    first_now = datetime.now(UTC)
    second_now = first_now + timedelta(minutes=10)

    try:
        with TestSessionLocal.begin() as db:
            first = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "a")],
                worker_id="worker-1",
                now=first_now,
                claim_expires_at=first_now + timedelta(minutes=5),
                limit=1,
            )[0]

        with TestSessionLocal.begin() as db:
            second = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[_candidate(article_ids[0], "b")],
                worker_id="worker-2",
                now=second_now,
                claim_expires_at=second_now + timedelta(minutes=5),
                limit=1,
            )[0]

        with pytest.raises(
            ArticleProcessingLeaseLostError
        ):
            with TestSessionLocal.begin() as db:
                repository.complete(
                    db,
                    state_id=first.state_id,
                    run_id=first.run_id,
                    worker_id="worker-1",
                    now=second_now + timedelta(seconds=1),
                )

        with TestSessionLocal() as db:
            state = db.get(
                ArticleProcessingState,
                second.state_id,
            )

            assert state.processed_input_hash is None
            assert state.claimed_by == "worker-2"

    finally:
        _cleanup_source(source_id)


def test_invalidate_processed_forces_reprocessing():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    candidate = _candidate(article_ids[0], "a")
    now = datetime.now(UTC)

    try:
        with TestSessionLocal.begin() as db:
            first = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )[0]

            repository.complete(
                db,
                state_id=first.state_id,
                run_id=first.run_id,
                worker_id="worker-1",
                now=now + timedelta(seconds=1),
            )

        with TestSessionLocal.begin() as db:
            assert (
                repository.claim_candidates(
                    db,
                    pipeline=PIPELINE,
                    candidates=[candidate],
                    worker_id="worker-2",
                    now=now + timedelta(minutes=1),
                    claim_expires_at=now + timedelta(minutes=6),
                    limit=1,
                )
                == []
            )

            assert repository.invalidate_processed(
                db,
                pipeline=PIPELINE,
                article_ids=article_ids,
            ) == 1

        with TestSessionLocal.begin() as db:
            claims = repository.claim_candidates(
                db,
                pipeline=PIPELINE,
                candidates=[candidate],
                worker_id="worker-2",
                now=now + timedelta(minutes=2),
                claim_expires_at=now + timedelta(minutes=7),
                limit=1,
            )

            assert len(claims) == 1
            assert claims[0].attempt_number == 2

    finally:
        _cleanup_source(source_id)