from datetime import UTC, datetime
from uuid import uuid4

from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.search.builder import SearchDocumentBuilder
from app.services.search_indexing import SearchIndexingService


class StubRepository:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    def get_by_article_id(self, db, article_id, *, include_deleted=False):
        return self.existing

    def hard_delete(self, db, document):
        self.existing = None


    def add(self, db, document):
        self.added.append(document)
        return document


def make_article():
    now = datetime(2026, 7, 21, tzinfo=UTC)
    source = Source(id=uuid4(), name="Example", normalized_name="example", slug="example")
    feed = Feed(id=uuid4(), source_id=source.id, source=source, name="Main", url="https://example.test/feed")
    return Article(
        id=uuid4(), feed_id=feed.id, feed=feed, normalized_title="Title",
        normalized_text="Body", content_hash="b" * 64, normalized_at=now,
    )


def test_index_article_creates_missing_document():
    repository = StubRepository()
    service = SearchIndexingService(repository=repository, builder=SearchDocumentBuilder())
    assert service.index_article(object(), make_article()) is True
    assert len(repository.added) == 1
    assert repository.added[0].title == "Title"


def test_index_article_updates_existing_document():
    existing = type("Document", (), {})()
    existing.deleted_at = None
    repository = StubRepository(existing)
    service = SearchIndexingService(repository=repository, builder=SearchDocumentBuilder())
    assert service.index_article(object(), make_article()) is False
    assert existing.body == "Body"
    assert repository.added == []
