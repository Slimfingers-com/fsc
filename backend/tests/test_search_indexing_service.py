from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)
from app.models.feed import Feed
from app.models.search_document import SearchDocument
from app.models.source import Source
from app.repositories.search_document import SearchDocumentRepository
from app.search.builder import SearchDocumentBuilder
from app.services.search_indexing import (
    SearchIndexingRunner,
    SearchIndexingService,
)
from tests.conftest import TestSessionLocal


class StubRepository:
    def __init__(
        self,
        existing=None,
    ):
        self.existing = existing
        self.added = []

    def get_by_article_id(
        self,
        db,
        article_id,
        *,
        include_deleted=False,
    ):
        return self.existing

    def hard_delete(
        self,
        db,
        document,
    ):
        self.existing = None

    def add(
        self,
        db,
        document,
    ):
        self.added.append(
            document
        )
        return document


def make_article():
    now = datetime(
        2026,
        7,
        21,
        tzinfo=UTC,
    )

    source = Source(
        id=uuid4(),
        name="Example",
        normalized_name="example",
        slug="example",
    )

    feed = Feed(
        id=uuid4(),
        source_id=source.id,
        source=source,
        name="Main",
        url="https://example.test/feed",
    )

    return Article(
        id=uuid4(),
        feed_id=feed.id,
        feed=feed,
        normalized_title="Title",
        normalized_text="Body",
        content_hash="b" * 64,
        normalized_at=now,
    )


def _create_normalized_article():
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

        article = Article(
            feed=feed,
            identity_type=ArticleIdentityType.DERIVED,
            identity_key=token.ljust(64, "0")[:64],
            normalized_title="Title",
            normalized_text="Body",
            language_code="en",
            content_hash="b" * 64,
            normalization_version=1,
            normalized_at=now,
            published_at=now,
            link=f"https://{token}.test/article",
        )

        db.add(article)
        db.flush()

        return (
            article.id,
            feed.id,
            source.id,
        )


def test_index_article_creates_missing_document():
    repository = StubRepository()

    service = SearchIndexingService(
        repository=repository,
        builder=SearchDocumentBuilder(),
    )

    assert service.index_article(
        object(),
        make_article(),
    ) is True

    assert len(repository.added) == 1
    assert repository.added[0].title == "Title"


def test_index_article_updates_existing_document():
    existing = type(
        "Document",
        (),
        {},
    )()
    existing.deleted_at = None

    repository = StubRepository(
        existing
    )

    service = SearchIndexingService(
        repository=repository,
        builder=SearchDocumentBuilder(),
    )

    assert service.index_article(
        object(),
        make_article(),
    ) is False

    assert existing.body == "Body"
    assert repository.added == []


def test_candidate_tracks_search_document_identity():
    article = make_article()
    service = SearchIndexingService()

    first = service.candidate(
        article
    )

    article.link = "https://example.test/changed"

    second = service.candidate(
        article
    )

    assert first.input_hash != second.input_hash
    assert first.provider == "search_document_builder"
    assert first.provider_version == str(
        SearchDocumentBuilder.VERSION
    )
    assert first.configuration_version == "1"


def test_runner_indexes_and_records_success():
    article_id, _, _ = (
        _create_normalized_article()
    )

    runner = SearchIndexingRunner(
        TestSessionLocal,
        worker_id="search-test",
    )

    result = runner.run_pending(
        limit=1
    )

    assert result.processed == 1
    assert result.created == 1
    assert result.updated == 0
    assert result.deleted == 0

    with TestSessionLocal() as db:
        document = db.scalar(
            select(SearchDocument).where(
                SearchDocument.article_id
                == article_id
            )
        )

        state = db.scalar(
            select(ArticleProcessingState).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.SEARCH_INDEXING.value,
            )
        )

        run = db.scalar(
            select(ArticleProcessingRun).where(
                ArticleProcessingRun.article_id
                == article_id,
                ArticleProcessingRun.pipeline
                == ArticlePipeline.SEARCH_INDEXING.value,
            )
        )

        assert document is not None

        assert state is not None
        assert state.processed_input_hash is not None
        assert state.claimed_by is None
        assert state.attempt_count == 1

        assert run is not None
        assert run.outcome == "succeeded"
        assert run.finished_at is not None


def test_runner_does_not_index_unchanged_article_twice():
    article_id, _, _ = (
        _create_normalized_article()
    )

    runner = SearchIndexingRunner(
        TestSessionLocal,
        worker_id="search-test",
    )

    first = runner.run_pending(
        limit=1
    )
    second = runner.run_pending(
        limit=1
    )

    assert first.processed == 1
    assert second.processed == 0

    with TestSessionLocal() as db:
        runs = list(
            db.scalars(
                select(ArticleProcessingRun).where(
                    ArticleProcessingRun.article_id
                    == article_id,
                    ArticleProcessingRun.pipeline
                    == ArticlePipeline.SEARCH_INDEXING.value,
                )
            )
        )

        assert len(runs) == 1


def test_reactivated_feed_is_reindexed():
    article_id, feed_id, _ = (
        _create_normalized_article()
    )

    runner = SearchIndexingRunner(
        TestSessionLocal,
        worker_id="search-test",
    )

    assert runner.run_pending(
        limit=1
    ).created == 1

    with TestSessionLocal.begin() as db:
        feed = db.get(
            Feed,
            feed_id,
        )
        feed.active = False

    inactive_result = runner.run_pending(
        limit=1
    )

    assert inactive_result.deleted == 1
    assert inactive_result.processed == 0

    with TestSessionLocal() as db:
        assert (
            SearchDocumentRepository()
            .get_by_article_id(
                db,
                article_id,
            )
            is None
        )

    with TestSessionLocal.begin() as db:
        feed = db.get(
            Feed,
            feed_id,
        )
        feed.active = True

    reactivated_result = runner.run_pending(
        limit=1
    )

    assert reactivated_result.created == 1
    assert reactivated_result.processed == 1

    with TestSessionLocal() as db:
        assert (
            SearchDocumentRepository()
            .get_by_article_id(
                db,
                article_id,
            )
            is not None
        )

        runs = list(
            db.scalars(
                select(ArticleProcessingRun).where(
                    ArticleProcessingRun.article_id
                    == article_id,
                    ArticleProcessingRun.pipeline
                    == ArticlePipeline.SEARCH_INDEXING.value,
                )
                .order_by(
                    ArticleProcessingRun.attempt_number
                )
            )
        )

        assert len(runs) == 2
        assert [
            run.attempt_number
            for run in runs
        ] == [1, 2]