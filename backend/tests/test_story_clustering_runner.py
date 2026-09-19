from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

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
) -> StoryClusteringRunner:
    service = StoryClusteringService(
        clusterer=RuleBasedStoryClusterer(),
    )

    return StoryClusteringRunner(
        TestSessionLocal,
        service,
        worker_id=worker_id,
        clock=clock,
        claim_ttl_seconds=claim_ttl_seconds,
        window_hours=24.0,
        candidate_limit=100,
    )


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
