from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import ArticleProcessingState
from app.models.feed import Feed
from app.models.source import Source
from app.services.semantic_embedding import (
    SemanticEmbeddingRunner,
    SemanticEmbeddingService,
)
from tests.conftest import TestSessionLocal


class VersionedProvider:
    provider = "test-semantic"
    model = "test-semantic-model"
    dimensions = 2

    def __init__(self, version: str) -> None:
        self.version = version

    def embed(self, texts):
        return tuple((1.0, 0.0) for _ in texts)


def create_committed_articles(
    count: int,
    *,
    created_at: datetime | None = None,
) -> list:
    token = uuid4().hex
    now = created_at or datetime.now(UTC)

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
                identity_key=(uuid4().hex * 2),
                title="Semantic priority test",
                normalized_title="semantic priority test",
                normalized_text=f"Normalized body {index}",
                language_code="en",
                content_hash=(uuid4().hex * 2),
                normalization_version=1,
                normalized_at=now,
                published_at=now,
                created_at=now + timedelta(microseconds=index),
            )
            for index in range(count)
        ]
        db.add_all(articles)
        db.flush()
        return [article.id for article in articles]


def make_runner(
    *,
    worker_id: str,
    provider_version: str = "1",
    live_claim_fraction: float = 0.8,
) -> SemanticEmbeddingRunner:
    service = SemanticEmbeddingService(
        provider=VersionedProvider(provider_version),
        include_article_embeddings=False,
    )
    return SemanticEmbeddingRunner(
        TestSessionLocal,
        service,
        worker_id=worker_id,
        live_claim_fraction=live_claim_fraction,
    )


def test_runner_prioritizes_newest_unprocessed_articles():
    old_article_ids = create_committed_articles(
        3,
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    newest_article_id = create_committed_articles(
        1,
        created_at=datetime(2026, 10, 5, tzinfo=UTC),
    )[0]

    runner = make_runner(
        worker_id="newest-live-semantic-worker",
    )
    result = runner.run_pending(limit=1)

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (1, 1, 0, 0)

    with TestSessionLocal() as db:
        processed_ids = set(
            db.scalars(
                select(ArticleProcessingState.article_id).where(
                    ArticleProcessingState.pipeline
                    == ArticlePipeline.SEMANTIC_EMBEDDING.value,
                    ArticleProcessingState.processed_input_hash.is_not(None),
                )
            )
        )

    assert newest_article_id in processed_ids
    assert not processed_ids.intersection(old_article_ids)


def test_runner_prioritizes_live_work_and_reserves_backfill_capacity():
    old_article_ids = create_committed_articles(3)

    initial_runner = make_runner(
        worker_id="initial-semantic-worker",
    )
    initial = initial_runner.run_pending(limit=3)
    assert initial.processed == 3

    live_article_id = create_committed_articles(1)[0]

    runner = make_runner(
        worker_id="priority-semantic-worker",
        provider_version="2",
        live_claim_fraction=0.5,
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
                select(ArticleProcessingState).where(
                    ArticleProcessingState.article_id.in_(
                        [*old_article_ids, live_article_id]
                    ),
                    ArticleProcessingState.pipeline
                    == ArticlePipeline.SEMANTIC_EMBEDDING.value,
                )
            )
        }

    assert (
        states[live_article_id].processed_provider_version
        == "2"
    )
    assert sum(
        states[article_id].processed_provider_version == "2"
        for article_id in old_article_ids
    ) == 1


def test_runner_reuses_unused_backfill_capacity_for_live_work():
    article_ids = create_committed_articles(3)

    runner = make_runner(
        worker_id="live-capacity-semantic-worker",
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
            .select_from(ArticleProcessingState)
            .where(
                ArticleProcessingState.article_id.in_(article_ids),
                ArticleProcessingState.pipeline
                == ArticlePipeline.SEMANTIC_EMBEDDING.value,
                ArticleProcessingState.processed_input_hash.is_not(None),
            )
        )

    assert processed_count == 3


def test_runner_reuses_unused_live_capacity_for_backfill_work():
    article_ids = create_committed_articles(3)

    initial_runner = make_runner(
        worker_id="initial-backfill-semantic-worker",
    )
    initial = initial_runner.run_pending(limit=3)
    assert initial.processed == 3

    runner = make_runner(
        worker_id="backfill-capacity-semantic-worker",
        provider_version="2",
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
        upgraded_count = db.scalar(
            select(func.count())
            .select_from(ArticleProcessingState)
            .where(
                ArticleProcessingState.article_id.in_(article_ids),
                ArticleProcessingState.pipeline
                == ArticlePipeline.SEMANTIC_EMBEDDING.value,
                ArticleProcessingState.processed_provider_version == "2",
            )
        )

    assert upgraded_count == 3
