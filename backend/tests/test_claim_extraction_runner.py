from concurrent.futures import (
    ThreadPoolExecutor,
)
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from app.claims.rule_based import (
    RuleBasedClaimExtractor,
)
from app.enums.article_identity_type import (
    ArticleIdentityType,
)
from app.enums.article_pipeline import (
    ArticlePipeline,
)
from app.enums.source_type import (
    SourceType,
)
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source
from app.services.claim_extraction import (
    ClaimExtractionRunner,
    ClaimExtractionService,
)
from tests.conftest import (
    TestSessionLocal,
)


def create_committed_articles(
    count: int,
):
    token = uuid4().hex
    now = datetime.now(UTC)

    with TestSessionLocal.begin() as db:
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=(
                f"https://{token}.test"
            ),
            source_type=(
                SourceType.NEWS
            ),
        )
        feed = Feed(
            source=source,
            name="Main",
            url=(
                f"https://{token}.test/feed"
            ),
        )
        articles = []

        for index in range(
            count
        ):
            article = Article(
                feed=feed,
                identity_type=(
                    ArticleIdentityType
                    .DERIVED
                ),
                identity_key=(
                    f"{index:064d}"
                ),
                normalized_title="Update",
                normalized_text=(
                    "The government approved "
                    f"climate package number {index} today."
                ),
                language_code="en",
                content_hash=(
                    f"{index + 1:064x}"
                ),
                normalization_version=1,
                normalized_at=now,
            )
            db.add(
                article
            )
            articles.append(
                article
            )

        db.flush()
        return [
            article.id
            for article in articles
        ]


def make_runner(
    worker_id: str,
):
    return ClaimExtractionRunner(
        TestSessionLocal,
        ClaimExtractionService(
            extractor=(
                RuleBasedClaimExtractor()
            )
        ),
        worker_id=worker_id,
    )


def test_runner_processes_once_and_reprocesses_changed_input():
    article_id = (
        create_committed_articles(
            1
        )[0]
    )
    runner = make_runner(
        "claim-worker"
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

    assert second.selected == 0

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            article_id,
        )
        assert article is not None
        article.normalized_text = (
            "The government approved a revised climate package today."
        )
        article.content_hash = (
            "f" * 64
        )

    third = runner.run_pending(
        limit=1
    )

    assert third.processed == 1

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticleClaim
            )
            .where(
                ArticleClaim.article_id
                == article_id
            )
        ) == 2

        assert db.scalar(
            select(func.count())
            .select_from(
                ArticleClaim
            )
            .where(
                ArticleClaim.article_id
                == article_id,
                ArticleClaim.deleted_at
                .is_(None),
            )
        ) == 1

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline
                .CLAIM_EXTRACTION
                .value,
            )
        )
        assert state is not None
        assert state.attempt_count == 2


def test_parallel_workers_do_not_duplicate_active_claims():
    article_ids = (
        create_committed_articles(
            6
        )
    )

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        results = list(
            executor.map(
                lambda worker: (
                    make_runner(
                        worker
                    ).run_pending(
                        limit=3
                    )
                ),
                (
                    "worker-a",
                    "worker-b",
                ),
            )
        )

    assert sorted(
        result.selected
        for result in results
    ) == [3, 3]
    assert sorted(
        result.processed
        for result in results
    ) == [3, 3]

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticleClaim
            )
            .where(
                ArticleClaim.deleted_at
                .is_(None)
            )
        ) == 6

        claimed_article_ids = set(
            db.scalars(
                select(
                    ArticleClaim.article_id
                ).where(
                    ArticleClaim.deleted_at
                    .is_(None)
                )
            ).all()
        )

        assert claimed_article_ids == set(
            article_ids
        )

        assert db.scalar(
            select(func.count())
            .select_from(
                ArticleProcessingRun
            )
            .where(
                ArticleProcessingRun.pipeline
                == ArticlePipeline
                .CLAIM_EXTRACTION
                .value,
                ArticleProcessingRun.outcome
                == "succeeded",
            )
        ) == 6
