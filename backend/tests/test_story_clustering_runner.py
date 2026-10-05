from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, text

from app.clustering.provider import StoryClusteringInput
from app.clustering.rule_based import RuleBasedStoryClusterer
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
from app.models.story import Story, StoryArticle
from app.repositories.story import StoryRepository
from app.services.story_clustering import (
    StoryClusteringRunner,
    StoryClusteringService,
)
from tests.conftest import TestSessionLocal


def create_committed_articles(
    count: int,
) -> list:
    token = uuid4().hex
    now = datetime.now(UTC)

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
                identity_type=(
                    ArticleIdentityType.DERIVED
                ),
                identity_key=f"{index:064d}",
                title="Berlin election update",
                normalized_title=(
                    "berlin election update"
                ),
                normalized_text=(
                    f"Normalized body {index}"
                ),
                language_code="en",
                content_hash=f"{index:064x}",
                normalization_version=1,
                normalized_at=now,
                published_at=now,
                created_at=(
                    now
                    + timedelta(
                        microseconds=index
                    )
                ),
            )
            for index in range(count)
        ]

        db.add_all(articles)
        db.flush()

        return [
            article.id
            for article in articles
        ]


def make_runner(
    *,
    worker_id: str,
    clock=None,
    claim_ttl_seconds: float = 300,
    candidate_limit: int = 100,
    live_claim_fraction: float = 0.8,
    clusterer=None,
) -> StoryClusteringRunner:
    service = StoryClusteringService(
        clusterer=(
            clusterer
            or RuleBasedStoryClusterer()
        ),
    )

    return StoryClusteringRunner(
        TestSessionLocal,
        service,
        worker_id=worker_id,
        clock=clock,
        claim_ttl_seconds=claim_ttl_seconds,
        window_hours=24.0,
        candidate_limit=candidate_limit,
        live_claim_fraction=live_claim_fraction,
    )


def test_runner_prioritizes_live_work_and_reserves_backfill_capacity():
    old_article_ids = create_committed_articles(3)

    initial_runner = make_runner(
        worker_id="initial-story-worker",
    )
    initial = initial_runner.run_pending(limit=3)
    assert initial.processed == 3

    live_article_id = create_committed_articles(1)[0]

    class NextVersionClusterer(
        RuleBasedStoryClusterer
    ):
        version = "priority-test"

    runner = make_runner(
        worker_id="priority-story-worker",
        live_claim_fraction=0.5,
        clusterer=NextVersionClusterer(),
    )
    result = runner.run_pending(limit=2)

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (2, 2, 0, 0)

    with TestSessionLocal() as db:
        states = {
            state.article_id: state
            for state in db.scalars(
                select(
                    ArticleProcessingState
                ).where(
                    ArticleProcessingState.article_id.in_(
                        [
                            *old_article_ids,
                            live_article_id,
                        ]
                    ),
                    ArticleProcessingState.pipeline
                    == ArticlePipeline.STORY_CLUSTERING.value,
                )
            )
        }

    assert (
        states[
            live_article_id
        ].processed_provider_version
        == "priority-test"
    )
    assert sum(
        states[
            article_id
        ].processed_provider_version
        == "priority-test"
        for article_id in old_article_ids
    ) == 1


def test_runner_reuses_unused_backfill_capacity_for_live_work():
    article_ids = create_committed_articles(3)

    runner = make_runner(
        worker_id="live-capacity-worker",
        live_claim_fraction=0.5,
    )
    result = runner.run_pending(limit=3)

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (3, 3, 0, 0)

    with TestSessionLocal() as db:
        processed_count = db.scalar(
            select(func.count())
            .select_from(
                ArticleProcessingState
            )
            .where(
                ArticleProcessingState.article_id.in_(
                    article_ids
                ),
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
                ArticleProcessingState.processed_input_hash
                .is_not(None),
            )
        )

    assert processed_count == 3


def test_runner_reuses_unused_live_capacity_for_backfill_work():
    article_ids = create_committed_articles(3)

    initial_runner = make_runner(
        worker_id="initial-backfill-worker",
    )
    initial = initial_runner.run_pending(limit=3)
    assert initial.processed == 3

    class NextVersionClusterer(
        RuleBasedStoryClusterer
    ):
        version = "backfill-capacity-test"

    runner = make_runner(
        worker_id="backfill-capacity-worker",
        live_claim_fraction=0.5,
        clusterer=NextVersionClusterer(),
    )
    result = runner.run_pending(limit=3)

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (3, 3, 0, 0)

    with TestSessionLocal() as db:
        upgraded_count = db.scalar(
            select(func.count())
            .select_from(
                ArticleProcessingState
            )
            .where(
                ArticleProcessingState.article_id.in_(
                    article_ids
                ),
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
                ArticleProcessingState.processed_provider_version
                == "backfill-capacity-test",
            )
        )

    assert upgraded_count == 3


def test_runner_processes_article_and_does_not_reclaim_unchanged_input():
    article_id = create_committed_articles(
        1
    )[0]

    runner = make_runner(
        worker_id="story-worker",
    )

    first = runner.run_pending(
        limit=1
    )

    assert (
        first.selected,
        first.processed,
        first.skipped,
        first.failed,
    ) == (
        1,
        1,
        0,
        0,
    )

    second = runner.run_pending(
        limit=1
    )

    assert (
        second.selected,
        second.processed,
        second.skipped,
        second.failed,
    ) == (
        0,
        0,
        0,
        0,
    )

    with TestSessionLocal() as db:
        membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == article_id
            )
        )

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        run = db.scalar(
            select(
                ArticleProcessingRun
            ).where(
                ArticleProcessingRun.article_id
                == article_id,
                ArticleProcessingRun.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        assert membership is not None
        assert state is not None
        assert run is not None

        assert (
            membership.processing_run_id
            == run.id
        )

        assert membership.match_kind == "created"
        assert run.outcome == "succeeded"

        assert (
            state.processed_provider
            == RuleBasedStoryClusterer.provider
        )
        assert state.claimed_by is None


def test_lease_loss_during_completion_rolls_back_story_write():
    article_id = create_committed_articles(
        1
    )[0]

    start = datetime(
        2026,
        9,
        19,
        10,
        0,
        tzinfo=UTC,
    )

    moments = iter(
        (
            start,
            start + timedelta(seconds=1),
            start + timedelta(seconds=12),
            start + timedelta(seconds=13),
        )
    )

    runner = make_runner(
        worker_id="lease-worker",
        clock=lambda: next(moments),
        claim_ttl_seconds=10,
    )

    result = runner.run_pending(
        limit=1
    )

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (
        1,
        0,
        1,
        0,
    )

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(StoryArticle)
        ) == 0

        assert db.scalar(
            select(func.count())
            .select_from(Story)
        ) == 0

        run = db.scalar(
            select(
                ArticleProcessingRun
            ).where(
                ArticleProcessingRun.article_id
                == article_id,
                ArticleProcessingRun.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        assert run is not None
        assert run.outcome == "lease_lost"


def test_parallel_workers_cluster_same_story_from_same_feed():
    article_ids = create_committed_articles(
        2
    )

    runners = [
        make_runner(
            worker_id=f"story-worker-{index}",
        )
        for index in range(2)
    ]

    with ThreadPoolExecutor(
        max_workers=2
    ) as pool:
        results = list(
            pool.map(
                lambda runner: (
                    runner.run_pending(
                        limit=1
                    )
                ),
                runners,
            )
        )

    assert sum(
        result.selected
        for result in results
    ) == 2

    assert sum(
        result.processed
        for result in results
    ) == 2

    assert sum(
        result.skipped
        for result in results
    ) == 0

    assert sum(
        result.failed
        for result in results
    ) == 0

    with TestSessionLocal() as db:
        memberships = list(
            db.scalars(
                select(
                    StoryArticle
                ).where(
                    StoryArticle.article_id.in_(
                        article_ids
                    ),
                    StoryArticle.deleted_at.is_(
                        None
                    ),
                )
            )
        )

        runs = list(
            db.scalars(
                select(
                    ArticleProcessingRun
                ).where(
                    ArticleProcessingRun.article_id.in_(
                        article_ids
                    ),
                    ArticleProcessingRun.pipeline
                    == ArticlePipeline.STORY_CLUSTERING.value,
                )
            )
        )

        assert len(memberships) == 2
        assert len(runs) == 2

        assert len(
            {
                membership.article_id
                for membership in memberships
            }
        ) == 2

        assert len(
            {
                membership.story_id
                for membership in memberships
            }
        ) == 1

        assert sorted(
            membership.match_kind
            for membership in memberships
        ) == [
            "created",
            "matched",
        ]

        assert all(
            run.outcome == "succeeded"
            for run in runs
        )

def test_runner_reclusters_article_after_feed_is_reactivated():
    article_id = create_committed_articles(
        1
    )[0]

    runner = make_runner(
        worker_id="cleanup-worker",
    )

    first = runner.run_pending(
        limit=1
    )

    assert first.processed == 1

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            article_id,
        )

        feed = db.get(
            Feed,
            article.feed_id,
        )

        feed.active = False

    second = runner.run_pending(
        limit=1
    )

    assert second.selected == 0

    with TestSessionLocal() as db:
        membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == article_id
            )
        )

        assert membership is not None
        assert membership.deleted_at is not None

        story = db.get(
            Story,
            membership.story_id,
        )

        assert story is not None
        assert story.deleted_at is not None

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        assert state is not None
        assert state.processed_input_hash is None
        assert state.last_processed_at is None

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            article_id,
        )

        feed = db.get(
            Feed,
            article.feed_id,
        )

        feed.active = True

    third = runner.run_pending(
        limit=1
    )

    assert (
        third.selected,
        third.processed,
        third.skipped,
        third.failed,
    ) == (
        1,
        1,
        0,
        0,
    )

    with TestSessionLocal() as db:
        active_membership_count = db.scalar(
            select(func.count())
            .select_from(StoryArticle)
            .where(
                StoryArticle.article_id
                == article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        assert active_membership_count == 1
        assert state is not None
        assert state.processed_input_hash is not None
        assert state.last_processed_at is not None

def test_runner_preserves_singleton_story_on_reprocessing_without_match():
    article_id = create_committed_articles(
        1
    )[0]

    runner = make_runner(
        worker_id="singleton-worker",
    )

    first = runner.run_pending(
        limit=1
    )

    assert first.processed == 1

    with TestSessionLocal() as db:
        first_membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        assert first_membership is not None
        original_story_id = (
            first_membership.story_id
        )

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            article_id,
        )

        article.title = (
            "Completely changed singleton title"
        )
        article.normalized_title = (
            "completely changed singleton title"
        )

    second = runner.run_pending(
        limit=1
    )

    assert second.processed == 1

    with TestSessionLocal() as db:
        active_membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        memberships = list(
            db.scalars(
                select(
                    StoryArticle
                ).where(
                    StoryArticle.article_id
                    == article_id
                )
            )
        )

        assert active_membership is not None
        assert (
            active_membership.story_id
            == original_story_id
        )
        assert (
            active_membership.match_kind
            == "retained"
        )
        assert len(memberships) == 2

def test_runner_acquires_story_lock_before_processing_heartbeat(
    monkeypatch,
):
    article_id = create_committed_articles(
        1
    )[0]

    runner = make_runner(
        worker_id="lock-order-worker",
    )

    events = []

    original_lock = (
        runner.service.repository
        .acquire_processing_coordination_lock
    )

    original_heartbeat = (
        runner.processing_repository
        .heartbeat
    )

    def acquire_lock(db):
        events.append("lock")
        return original_lock(db)

    def heartbeat(db, **kwargs):
        events.append("heartbeat")
        return original_heartbeat(
            db,
            **kwargs,
        )

    monkeypatch.setattr(
        runner.service.repository,
        "acquire_processing_coordination_lock",
        acquire_lock,
    )

    monkeypatch.setattr(
        runner.processing_repository,
        "heartbeat",
        heartbeat,
    )

    result = runner.run_pending(
        limit=1
    )

    assert result.processed == 1

    heartbeat_index = events.index(
        "heartbeat"
    )

    assert "lock" in events[:heartbeat_index]

def test_story_mutation_lock_serializes_cross_language_clustering():
    repository = StoryRepository()

    with TestSessionLocal.begin() as first_db:
        repository.acquire_processing_coordination_lock(
            first_db
        )
        repository.acquire_clustering_lock(
            first_db
        )

        with TestSessionLocal.begin() as second_db:
            shared_coordination = second_db.scalar(
                text(
                    "SELECT "
                    "pg_try_advisory_xact_lock_shared"
                    "(:lock_key)"
                ),
                {
                    "lock_key": (
                        repository.CLUSTERING_LOCK_KEY
                    )
                },
            )
            mutation_acquired = second_db.scalar(
                text(
                    "SELECT "
                    "pg_try_advisory_xact_lock"
                    "(:lock_key)"
                ),
                {
                    "lock_key": (
                        repository.STORY_MUTATION_LOCK_KEY
                    )
                },
            )
            cleanup_acquired = second_db.scalar(
                text(
                    "SELECT "
                    "pg_try_advisory_xact_lock"
                    "(:lock_key)"
                ),
                {
                    "lock_key": (
                        repository.CLUSTERING_LOCK_KEY
                    )
                },
            )

            assert shared_coordination is True
            assert mutation_acquired is False
            assert cleanup_acquired is False


def test_story_row_mutation_lock_is_compatible_with_key_share():
    repository = StoryRepository()

    with TestSessionLocal.begin() as setup_db:
        story = Story(language_code="en")
        setup_db.add(story)
        setup_db.flush()
        story_id = story.id

    with TestSessionLocal.begin() as first_db:
        held = first_db.scalar(
            select(Story)
            .where(Story.id == story_id)
            .with_for_update(
                of=Story,
                read=True,
                key_share=True,
            )
        )
        assert held is not None

        with TestSessionLocal.begin() as second_db:
            second_db.execute(
                text("SET LOCAL lock_timeout = '250ms'")
            )
            locked = repository.get_story(
                second_db,
                story_id,
                for_update=True,
            )

            assert locked is not None
            assert locked.id == story_id


def test_story_prepare_article_lock_is_compatible_with_key_share():
    article_id = create_committed_articles(1)[0]
    service = StoryClusteringService(
        clusterer=RuleBasedStoryClusterer(),
    )

    with TestSessionLocal.begin() as first_db:
        held = first_db.scalar(
            select(Article)
            .where(Article.id == article_id)
            .with_for_update(
                of=Article,
                read=True,
                key_share=True,
            )
        )
        assert held is not None

        with TestSessionLocal.begin() as second_db:
            second_db.execute(
                text("SET LOCAL lock_timeout = '250ms'")
            )
            prepared = service.prepare(
                second_db,
                article_id=article_id,
                window_hours=48.0,
                candidate_limit=250,
            )

            assert prepared is not None
            assert prepared.article.article_id == article_id


def test_runner_skips_claim_when_input_changes_before_processing(
    monkeypatch,
):
    article_id = create_committed_articles(
        1
    )[0]

    runner = make_runner(
        worker_id="changed-input-worker",
    )

    original_claim_pending = (
        runner._claim_pending
    )

    def claim_then_change(
        db,
        *,
        limit,
        now,
    ):
        claims = original_claim_pending(
            db,
            limit=limit,
            now=now,
        )

        with TestSessionLocal.begin() as other_db:
            article = other_db.get(
                Article,
                article_id,
            )

            article.title = (
                "Changed after story claim"
            )
            article.normalized_title = (
                "changed after story claim"
            )

        return claims

    monkeypatch.setattr(
        runner,
        "_claim_pending",
        claim_then_change,
    )

    result = runner.run_pending(
        limit=1
    )

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (
        1,
        0,
        1,
        0,
    )

    with TestSessionLocal() as db:
        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        run = db.scalar(
            select(
                ArticleProcessingRun
            ).where(
                ArticleProcessingRun.article_id
                == article_id,
                ArticleProcessingRun.pipeline
                == ArticlePipeline.STORY_CLUSTERING.value,
            )
        )

        membership_count = db.scalar(
            select(func.count())
            .select_from(StoryArticle)
        )

        assert state is not None
        assert run is not None

        assert state.claimed_by is None
        assert state.processed_input_hash is None
        assert run.outcome == "skipped"
        assert membership_count == 0

def test_runner_deactivates_old_story_immediately_after_story_move():
    article_ids = create_committed_articles(
        2
    )

    moving_article_id = article_ids[1]

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            moving_article_id,
        )

        article.title = "Completely unrelated report"
        article.normalized_title = (
            "completely unrelated report"
        )

    runner = make_runner(
        worker_id="story-move-worker",
    )

    first = runner.run_pending(
        limit=2
    )

    assert first.processed == 2

    with TestSessionLocal() as db:
        membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == moving_article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        assert membership is not None
        old_story_id = membership.story_id

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            moving_article_id,
        )

        article.title = "Berlin election update"
        article.normalized_title = (
            "berlin election update"
        )

    second = runner.run_pending(
        limit=1
    )

    assert second.processed == 1

    with TestSessionLocal() as db:
        active_membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == moving_article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        old_story = db.get(
            Story,
            old_story_id,
        )

        assert active_membership is not None
        assert (
            active_membership.story_id
            != old_story_id
        )

        assert old_story is not None
        assert old_story.deleted_at is not None

def test_candidate_limit_does_not_allow_one_story_to_hide_another():
    article_ids = create_committed_articles(
        4
    )

    exact_article_id = article_ids[0]

    with TestSessionLocal.begin() as db:
        exact_article = db.get(
            Article,
            exact_article_id,
        )
        exact_article.published_at = (
            exact_article.published_at
            - timedelta(hours=1)
        )

        for article_id in article_ids[1:]:
            article = db.get(
                Article,
                article_id,
            )

            article.title = (
                "Berlin economy outlook"
            )
            article.normalized_title = (
                "berlin economy outlook"
            )

    runner = make_runner(
        worker_id="candidate-fairness-worker",
        candidate_limit=2,
    )

    initial = runner.run_pending(
        limit=4
    )

    assert initial.processed == 4

    with TestSessionLocal() as db:
        exact_membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == exact_article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        assert exact_membership is not None
        exact_story_id = (
            exact_membership.story_id
        )

    query_article_id = (
        create_committed_articles(
            1
        )[0]
    )

    result = runner.run_pending(
        limit=1
    )

    assert result.processed == 1

    with TestSessionLocal() as db:
        query_membership = db.scalar(
            select(
                StoryArticle
            ).where(
                StoryArticle.article_id
                == query_article_id,
                StoryArticle.deleted_at.is_(
                    None
                ),
            )
        )

        assert query_membership is not None
        assert (
            query_membership.story_id
            == exact_story_id
        )
        assert (
            query_membership.match_kind
            == "matched"
        )

def test_runner_releases_story_lock_before_claim_scan(
    monkeypatch,
):
    create_committed_articles(
        1
    )

    runner = make_runner(
        worker_id="claim-scope-worker",
    )

    original_claim_pending = (
        runner._claim_pending
    )

    def claim_pending(
        db,
        *,
        limit,
        now,
    ):
        with TestSessionLocal.begin() as other_db:
            acquired = other_db.scalar(
                text(
                    "SELECT pg_try_advisory_xact_lock(:lock_key)"
                ),
                {
                    "lock_key": (
                        runner.service.repository
                        .CLUSTERING_LOCK_KEY
                    )
                },
            )

            assert acquired is True

        return original_claim_pending(
            db,
            limit=limit,
            now=now,
        )

    monkeypatch.setattr(
        runner,
        "_claim_pending",
        claim_pending,
    )

    result = runner.run_pending(
        limit=1
    )

    assert result.processed == 1


def test_candidate_discovery_allows_cross_language_shared_entities_without_semantics():
    article_ids = create_committed_articles(2)
    candidate_article_id, input_article_id = article_ids
    shared_entities = (uuid4(), uuid4())
    now = datetime.now(UTC)

    with TestSessionLocal.begin() as db:
        candidate_article = db.get(Article, candidate_article_id)
        input_article = db.get(Article, input_article_id)
        assert candidate_article is not None
        assert input_article is not None
        candidate_article.language_code = "en"
        input_article.language_code = "de"

        story = Story(language_code="en")
        db.add(story)
        db.flush()

        run = ArticleProcessingRun(
            article_id=candidate_article.id,
            processing_state_id=None,
            pipeline=ArticlePipeline.STORY_CLUSTERING.value,
            input_hash=uuid4().hex * 2,
            provider="test",
            provider_version="1",
            configuration_version="1",
            worker_id="test-worker",
            attempt_number=1,
            started_at=now,
            finished_at=now,
            outcome="succeeded",
        )
        db.add(run)
        db.flush()

        db.add(
            StoryArticle(
                story_id=story.id,
                article_id=candidate_article.id,
                processing_run_id=run.id,
                article_title=candidate_article.title,
                article_time=candidate_article.published_at or candidate_article.created_at,
                title_terms=["budget", "parliament"],
                entity_ids=list(shared_entities),
                topic_ids=[],
                similarity_score=0.0,
                match_kind="created",
                match_details=None,
                clustered_at=now,
            )
        )
        db.flush()

        candidates = StoryRepository().list_candidates(
            db,
            article=StoryClusteringInput(
                article_id=input_article.id,
                language_code="de",
                article_time=input_article.published_at or input_article.created_at,
                title_terms=("haushalt", "bundestag"),
                entity_ids=shared_entities,
                topic_ids=(),
                semantic_embedding=None,
                semantic_model=None,
            ),
            window_hours=24.0,
            limit=100,
        )

    assert len(candidates) == 1
    assert candidates[0].article_id == candidate_article_id
    assert candidates[0].language_code == "en"
    assert candidates[0].entity_ids == shared_entities
