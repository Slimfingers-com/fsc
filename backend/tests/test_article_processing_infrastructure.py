from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun, ArticleProcessingState
from app.models.feed import Feed
from app.models.source import Source


def create_article(db) -> Article:
    source = Source(
        name="Processing Test Source",
        normalized_name="processing test source",
        slug="processing-test-source",
        url="https://processing.example.test",
        source_type=SourceType.NEWS,
    )
    feed = Feed(
        source=source,
        name="Processing Test Feed",
        url="https://processing.example.test/feed",
    )
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key="a" * 64,
    )
    db.add(article)
    db.flush()
    return article


def assert_flush_fails(db, obj) -> None:
    savepoint = db.begin_nested()
    db.add(obj)

    try:
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        if savepoint.is_active:
            savepoint.rollback()


def test_processing_state_accepts_empty_processed_identity(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(state)
    db.flush()

    assert state.id is not None
    assert state.processed_input_hash is None
    assert state.last_processed_at is None


def test_processing_state_accepts_complete_processed_identity(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        processed_input_hash="b" * 64,
        processed_provider="test-provider",
        processed_provider_version="1",
        processed_configuration_version="1",
        last_processed_at=datetime.now(UTC),
    )
    db.add(state)
    db.flush()

    assert state.id is not None


def test_processing_state_rejects_partial_processed_identity(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        processed_input_hash="b" * 64,
    )

    assert_flush_fails(db, state)


def test_processing_state_rejects_processed_identity_without_timestamp(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        processed_input_hash="b" * 64,
        processed_provider="test-provider",
        processed_provider_version="1",
        processed_configuration_version="1",
    )

    assert_flush_fails(db, state)


def test_processing_state_rejects_timestamp_without_processed_identity(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        last_processed_at=datetime.now(UTC),
    )

    assert_flush_fails(db, state)


def test_processing_state_accepts_complete_claim(db):
    article = create_article(db)
    now = datetime.now(UTC)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        claimed_input_hash="c" * 64,
        claimed_provider="test-provider",
        claimed_provider_version="1",
        claimed_configuration_version="1",
        claimed_at=now,
        claimed_by="worker-1",
        claim_expires_at=now + timedelta(minutes=5),
    )
    db.add(state)
    db.flush()

    assert state.id is not None


def test_processing_state_rejects_partial_claim(db):
    article = create_article(db)
    now = datetime.now(UTC)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        claimed_at=now,
        claimed_by="worker-1",
        claim_expires_at=now + timedelta(minutes=5),
    )

    assert_flush_fails(db, state)


def test_processing_state_rejects_nonfuture_claim_expiry(db):
    article = create_article(db)
    now = datetime.now(UTC)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        claimed_input_hash="c" * 64,
        claimed_provider="test-provider",
        claimed_provider_version="1",
        claimed_configuration_version="1",
        claimed_at=now,
        claimed_by="worker-1",
        claim_expires_at=now,
    )

    assert_flush_fails(db, state)


def test_processing_state_rejects_negative_attempt_count(db):
    article = create_article(db)

    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
        attempt_count=-1,
    )

    assert_flush_fails(db, state)


def test_only_one_active_state_per_article_and_pipeline(db):
    article = create_article(db)

    first = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(first)
    db.flush()

    second = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )

    assert_flush_fails(db, second)


def test_soft_deleted_state_allows_replacement(db):
    article = create_article(db)

    first = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(first)
    db.flush()

    first.deleted_at = datetime.now(UTC)
    db.flush()

    replacement = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(replacement)
    db.flush()

    assert replacement.id != first.id


def test_different_pipelines_can_have_states_for_same_article(db):
    article = create_article(db)

    entity_topic = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    clustering = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.STORY_CLUSTERING.value,
    )
    db.add_all([entity_topic, clustering])
    db.flush()

    assert entity_topic.id != clustering.id


def create_run(
    article: Article,
    state: ArticleProcessingState | None,
    **overrides,
) -> ArticleProcessingRun:
    values = {
        "article_id": article.id,
        "processing_state_id": state.id if state is not None else None,
        "pipeline": ArticlePipeline.ENTITY_TOPIC.value,
        "input_hash": "d" * 64,
        "provider": "test-provider",
        "provider_version": "1",
        "configuration_version": "1",
        "worker_id": "worker-1",
        "attempt_number": 1,
        "started_at": datetime.now(UTC),
    }
    values.update(overrides)
    return ArticleProcessingRun(**values)


def test_processing_run_accepts_running_attempt(db):
    article = create_article(db)
    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(state)
    db.flush()

    run = create_run(article, state)
    db.add(run)
    db.flush()

    assert run.id is not None
    assert run.finished_at is None
    assert run.outcome is None


def test_processing_run_accepts_completed_attempt(db):
    article = create_article(db)
    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(state)
    db.flush()

    started_at = datetime.now(UTC)
    run = create_run(
        article,
        state,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=1),
        outcome="succeeded",
    )
    db.add(run)
    db.flush()

    assert run.outcome == "succeeded"


@pytest.mark.parametrize(
    "outcome",
    ["succeeded", "failed", "skipped", "lease_lost"],
)
def test_processing_run_accepts_supported_outcomes(db, outcome):
    article = create_article(db)
    started_at = datetime.now(UTC)

    run = create_run(
        article,
        None,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=1),
        outcome=outcome,
    )
    db.add(run)
    db.flush()

    assert run.outcome == outcome


def test_processing_run_rejects_nonpositive_attempt_number(db):
    article = create_article(db)

    run = create_run(
        article,
        None,
        attempt_number=0,
    )

    assert_flush_fails(db, run)


def test_processing_run_rejects_finish_before_start(db):
    article = create_article(db)
    started_at = datetime.now(UTC)

    run = create_run(
        article,
        None,
        started_at=started_at,
        finished_at=started_at - timedelta(seconds=1),
        outcome="failed",
    )

    assert_flush_fails(db, run)


def test_processing_run_rejects_unknown_outcome(db):
    article = create_article(db)
    started_at = datetime.now(UTC)

    run = create_run(
        article,
        None,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=1),
        outcome="unknown",
    )

    assert_flush_fails(db, run)


def test_processing_run_rejects_outcome_without_finished_at(db):
    article = create_article(db)

    run = create_run(
        article,
        None,
        outcome="succeeded",
    )

    assert_flush_fails(db, run)


def test_processing_run_rejects_finished_at_without_outcome(db):
    article = create_article(db)

    run = create_run(
        article,
        None,
        finished_at=datetime.now(UTC),
    )

    assert_flush_fails(db, run)


def test_deleting_processing_state_preserves_run(db):
    article = create_article(db)
    state = ArticleProcessingState(
        article_id=article.id,
        pipeline=ArticlePipeline.ENTITY_TOPIC.value,
    )
    db.add(state)
    db.flush()

    run = create_run(article, state)
    db.add(run)
    db.flush()

    run_id = run.id

    db.delete(state)
    db.flush()
    db.refresh(run)

    assert run.id == run_id
    assert run.processing_state_id is None