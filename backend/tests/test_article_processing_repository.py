from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete, select

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun, ArticleProcessingState
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.article_processing import (
    ArticleProcessingCandidate,
    ArticleProcessingLeaseLostError,
    ArticleProcessingRepository,
)
from tests.conftest import TestSessionLocal


def _create_articles(count: int) -> tuple[list, object]:
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

        return [article.id for article in articles], source.id


def _cleanup_source(source_id) -> None:
    with TestSessionLocal.begin() as db:
        article_ids = select(Article.id).join(Feed).where(
            Feed.source_id == source_id
        )

        db.execute(
            delete(ArticleProcessingRun).where(
                ArticleProcessingRun.article_id.in_(article_ids)
            )
        )

        db.execute(
            delete(Source).where(
                Source.id == source_id
            )
        )


def _candidate(article_id, suffix: str) -> ArticleProcessingCandidate:
    return ArticleProcessingCandidate(
        article_id=article_id,
        input_hash=(suffix * 64)[:64],
        provider="test-provider",
        provider_version="1",
        configuration_version="1",
    )


def test_ensure_state_is_idempotent():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    try:
        with TestSessionLocal.begin() as db:
            first = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )
            second = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )

            assert first.id == second.id

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id == article_ids[0],
                        ArticleProcessingState.pipeline
                        == ArticlePipeline.ENTITY_TOPIC.value,
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

    def ensure():
        repository = ArticleProcessingRepository()

        with TestSessionLocal.begin() as db:
            barrier.wait()
            state = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )
            return state.id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            state_ids = list(pool.map(lambda _: ensure(), range(2)))

        assert state_ids[0] == state_ids[1]

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id == article_ids[0],
                        ArticleProcessingState.pipeline
                        == ArticlePipeline.ENTITY_TOPIC.value,
                        ArticleProcessingState.deleted_at.is_(None),
                    )
                )
            )
            assert len(states) == 1
    finally:
        _cleanup_source(source_id)


def test_two_parallel_workers_claim_different_articles():
    article_ids, source_id = _create_articles(6)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    candidates = [
        _candidate(article_id, chr(97 + index))
        for index, article_id in enumerate(article_ids)
    ]

    with TestSessionLocal.begin() as db:
        for article_id in article_ids:
            repository.ensure_state(
                db,
                article_id=article_id,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )

    barrier = Barrier(2)

    def claim(worker_id):
        repo = ArticleProcessingRepository()

        with TestSessionLocal.begin() as db:
            barrier.wait()

            return repo.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
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

        first = set(results[0])
        second = set(results[1])

        assert len(first) == 3
        assert len(second) == 3
        assert first.isdisjoint(second)
        assert first | second == set(article_ids)

        with TestSessionLocal() as db:
            states = list(
                db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id.in_(article_ids)
                    )
                )
            )

            assert len(states) == 6
            assert {state.article_id for state in states} == set(article_ids)
            assert all(state.claimed_by is not None for state in states)
    finally:
        _cleanup_source(source_id)


def test_claim_preserves_article_specific_input_hash():
    article_ids, source_id = _create_articles(2)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    candidates = [
        _candidate(article_ids[0], "a"),
        _candidate(article_ids[1], "b"),
    ]

    try:
        with TestSessionLocal.begin() as db:
            claimed = repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=candidates,
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=2,
            )

            assert set(claimed) == set(article_ids)

        with TestSessionLocal() as db:
            states = {
                state.article_id: state
                for state in db.scalars(
                    select(ArticleProcessingState).where(
                        ArticleProcessingState.article_id.in_(article_ids)
                    )
                )
            }

            assert states[article_ids[0]].claimed_input_hash == "a" * 64
            assert states[article_ids[1]].claimed_input_hash == "b" * 64
    finally:
        _cleanup_source(source_id)


def test_already_processed_candidate_does_not_consume_limit():
    article_ids, source_id = _create_articles(2)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)

    first_candidate = _candidate(article_ids[0], "a")
    second_candidate = _candidate(article_ids[1], "b")

    try:
        with TestSessionLocal.begin() as db:
            first_state = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )

            repository.ensure_state(
                db,
                article_id=article_ids[1],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )

            first_state.processed_input_hash = first_candidate.input_hash
            first_state.processed_provider = first_candidate.provider
            first_state.processed_provider_version = (
                first_candidate.provider_version
            )
            first_state.processed_configuration_version = (
                first_candidate.configuration_version
            )
            first_state.last_processed_at = now

        with TestSessionLocal.begin() as db:
            claimed = repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[first_candidate, second_candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            assert claimed == [article_ids[1]]
    finally:
        _cleanup_source(source_id)


def test_start_run_copies_claim_identity():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)
    candidate = _candidate(article_ids[0], "a")

    try:
        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=now,
            )

            assert run.article_id == article_ids[0]
            assert run.processing_state_id == state.id
            assert run.pipeline == ArticlePipeline.ENTITY_TOPIC.value
            assert run.input_hash == candidate.input_hash
            assert run.provider == candidate.provider
            assert run.provider_version == candidate.provider_version
            assert run.configuration_version == candidate.configuration_version
            assert run.attempt_number == 1
    finally:
        _cleanup_source(source_id)


def test_heartbeat_extends_active_lease():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)
    candidate = _candidate(article_ids[0], "a")

    try:
        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=now,
            )

            extended = now + timedelta(minutes=10)

            assert repository.heartbeat(
                db,
                state_id=state.id,
                run_id=run.id,
                worker_id="worker-1",
                now=now + timedelta(minutes=1),
                claim_expires_at=extended,
            )

            db.flush()
            db.refresh(state)

            assert state.claim_expires_at == extended
    finally:
        _cleanup_source(source_id)


def test_complete_promotes_claim_identity_and_finishes_run():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()
    now = datetime.now(UTC)
    candidate = _candidate(article_ids[0], "a")

    try:
        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=now,
            )

            run_id = run.id
            finished_at = now + timedelta(seconds=10)

            repository.complete(
                db,
                state_id=state.id,
                run_id=run_id,
                worker_id="worker-1",
                now=finished_at,
            )

        with TestSessionLocal() as db:
            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )
            run = db.get(ArticleProcessingRun, run_id)

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

            assert state.claimed_at is None
            assert state.claimed_by is None
            assert state.claim_expires_at is None
            assert state.claimed_input_hash is None

            assert run.finished_at == finished_at
            assert run.outcome == "succeeded"
    finally:
        _cleanup_source(source_id)


def test_failure_preserves_previous_successful_identity():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    previous_at = datetime.now(UTC) - timedelta(hours=1)
    now = datetime.now(UTC)

    previous_candidate = _candidate(article_ids[0], "a")
    new_candidate = _candidate(article_ids[0], "b")

    try:
        with TestSessionLocal.begin() as db:
            state = repository.ensure_state(
                db,
                article_id=article_ids[0],
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
            )

            state.processed_input_hash = previous_candidate.input_hash
            state.processed_provider = previous_candidate.provider
            state.processed_provider_version = (
                previous_candidate.provider_version
            )
            state.processed_configuration_version = (
                previous_candidate.configuration_version
            )
            state.last_processed_at = previous_at

        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[new_candidate],
                worker_id="worker-1",
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=now,
            )

            run_id = run.id
            retry_after = now + timedelta(minutes=15)

            repository.fail(
                db,
                state_id=state.id,
                run_id=run_id,
                worker_id="worker-1",
                now=now + timedelta(seconds=1),
                retry_after=retry_after,
                error_code="provider_error",
                error_message="provider failed",
            )

        with TestSessionLocal() as db:
            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )
            run = db.get(ArticleProcessingRun, run_id)

            assert state.processed_input_hash == previous_candidate.input_hash
            assert state.last_processed_at == previous_at

            assert state.claimed_by is None
            assert state.claim_expires_at is None
            assert state.retry_after == retry_after
            assert state.last_error_code == "provider_error"

            assert run.outcome == "failed"
            assert run.error_code == "provider_error"
    finally:
        _cleanup_source(source_id)


def test_expired_lease_is_reclaimed_and_old_run_marked_lease_lost():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    first_now = datetime.now(UTC)
    second_now = first_now + timedelta(minutes=10)

    first_candidate = _candidate(article_ids[0], "a")
    second_candidate = _candidate(article_ids[0], "b")

    try:
        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[first_candidate],
                worker_id="worker-1",
                now=first_now,
                claim_expires_at=first_now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            old_run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=first_now,
            )

            old_run_id = old_run.id

        with TestSessionLocal.begin() as db:
            claimed = repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[second_candidate],
                worker_id="worker-2",
                now=second_now,
                claim_expires_at=second_now + timedelta(minutes=5),
                limit=1,
            )

            assert claimed == article_ids

        with TestSessionLocal() as db:
            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )
            old_run = db.get(ArticleProcessingRun, old_run_id)

            assert state.claimed_by == "worker-2"
            assert state.claimed_input_hash == second_candidate.input_hash
            assert state.attempt_count == 2

            assert old_run.outcome == "lease_lost"
            assert old_run.finished_at == second_now
            assert old_run.error_code == "lease_lost"
    finally:
        _cleanup_source(source_id)


def test_stale_worker_cannot_complete_after_reclaim():
    article_ids, source_id = _create_articles(1)
    repository = ArticleProcessingRepository()

    first_now = datetime.now(UTC)
    second_now = first_now + timedelta(minutes=10)

    first_candidate = _candidate(article_ids[0], "a")
    second_candidate = _candidate(article_ids[0], "b")

    try:
        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[first_candidate],
                worker_id="worker-1",
                now=first_now,
                claim_expires_at=first_now + timedelta(minutes=5),
                limit=1,
            )

            state = db.scalar(
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id == article_ids[0]
                )
            )

            old_run = repository.start_run(
                db,
                state=state,
                worker_id="worker-1",
                started_at=first_now,
            )

            state_id = state.id
            old_run_id = old_run.id

        with TestSessionLocal.begin() as db:
            repository.claim_candidates(
                db,
                pipeline=ArticlePipeline.ENTITY_TOPIC.value,
                candidates=[second_candidate],
                worker_id="worker-2",
                now=second_now,
                claim_expires_at=second_now + timedelta(minutes=5),
                limit=1,
            )

        with TestSessionLocal.begin() as db:
            try:
                repository.complete(
                    db,
                    state_id=state_id,
                    run_id=old_run_id,
                    worker_id="worker-1",
                    now=second_now + timedelta(seconds=1),
                )
            except ArticleProcessingLeaseLostError:
                pass
            else:
                raise AssertionError(
                    "stale worker unexpectedly completed processing"
                )

        with TestSessionLocal() as db:
            state = db.get(ArticleProcessingState, state_id)

            assert state.processed_input_hash is None
            assert state.claimed_by == "worker-2"
            assert state.claimed_input_hash == second_candidate.input_hash
    finally:
        _cleanup_source(source_id)