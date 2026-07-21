from datetime import UTC, datetime, timedelta

import pytest

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.search_document import SearchDocumentRepository
from app.search.builder import SearchDocumentBuilder
from app.services.search_indexing import SearchIndexingService


def create_indexed_article(db):
    now = datetime.now(UTC)
    source = Source(
        name="Example", normalized_name="example-review", slug="example-review",
        url="https://example.test", source_type=SourceType.NEWS,
    )
    feed = Feed(source=source, name="Main", url="https://example.test/review-feed")
    article = Article(
        feed=feed, identity_type=ArticleIdentityType.DERIVED,
        identity_key="review".ljust(64, "0"), normalized_title="Title",
        normalized_text="Body", language_code="en", content_hash="f" * 64,
        normalization_version=1, normalized_at=now, published_at=now,
        link="https://example.test/original",
    )
    db.add(article)
    db.flush()
    SearchIndexingService().index_article(db, article)
    db.flush()
    return article


@pytest.mark.parametrize("change", ["url", "published_at", "source"])
def test_pending_detection_covers_denormalized_fields(db, change):
    article = create_indexed_article(db)
    repository = SearchDocumentRepository()
    assert repository.list_pending_articles(
        db, builder_version=SearchDocumentBuilder.VERSION, limit=10
    ) == []
    if change == "url":
        article.link = "https://example.test/changed"
    elif change == "published_at":
        article.published_at += timedelta(hours=1)
    else:
        article.feed.source.name = "Renamed"
        article.feed.source.slug = "renamed-review"
    db.flush()
    assert repository.list_pending_articles(
        db, builder_version=SearchDocumentBuilder.VERSION, limit=10
    ) == [article]


def test_soft_deleted_document_is_hard_deleted_and_recreated(db):
    article = create_indexed_article(db)
    repository = SearchDocumentRepository()
    old_document = repository.get_by_article_id(db, article.id)
    old_id = old_document.id
    old_document.deleted_at = datetime.now(UTC)
    db.flush()
    assert repository.list_pending_articles(
        db, builder_version=SearchDocumentBuilder.VERSION, limit=10
    ) == [article]
    SearchIndexingService(repository=repository).index_article(db, article)
    db.flush()
    replacement = repository.get_by_article_id(db, article.id)
    assert replacement is not None
    assert replacement.id != old_id
    assert replacement.deleted_at is None


@pytest.mark.parametrize("ineligible", ["article", "feed", "source"])
def test_ineligible_documents_are_hard_deleted(db, ineligible):
    article = create_indexed_article(db)
    if ineligible == "article":
        article.deleted_at = datetime.now(UTC)
    elif ineligible == "feed":
        article.feed.active = False
    else:
        article.feed.source.deleted_at = datetime.now(UTC)
    db.flush()
    assert SearchDocumentRepository().delete_ineligible(db) == 1
    assert SearchDocumentRepository().get_by_article_id(db, article.id, include_deleted=True) is None
