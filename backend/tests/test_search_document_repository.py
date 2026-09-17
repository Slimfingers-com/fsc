from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.search_document import SearchDocumentRepository
from app.services.search_indexing import SearchIndexingService


def create_indexed_article(db):
    now = datetime.now(UTC)
    token = uuid4().hex

    source = Source(
        name=f"Example {token}",
        normalized_name=f"example-{token}",
        slug=f"example-{token}",
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
        content_hash="f" * 64,
        normalization_version=1,
        normalized_at=now,
        published_at=now,
        link=f"https://{token}.test/original",
    )

    db.add(article)
    db.flush()

    SearchIndexingService().index_article(
        db,
        article,
    )
    db.flush()

    return article


def test_get_by_article_id_returns_document(db):
    article = create_indexed_article(db)

    document = (
        SearchDocumentRepository()
        .get_by_article_id(
            db,
            article.id,
        )
    )

    assert document is not None
    assert document.article_id == article.id


def test_soft_deleted_document_can_be_loaded_explicitly(db):
    article = create_indexed_article(db)
    repository = SearchDocumentRepository()

    document = repository.get_by_article_id(
        db,
        article.id,
    )
    document.deleted_at = datetime.now(UTC)
    db.flush()

    assert (
        repository.get_by_article_id(
            db,
            article.id,
        )
        is None
    )

    assert (
        repository.get_by_article_id(
            db,
            article.id,
            include_deleted=True,
        )
        is document
    )


def test_indexing_recreates_soft_deleted_document(db):
    article = create_indexed_article(db)
    repository = SearchDocumentRepository()

    old_document = repository.get_by_article_id(
        db,
        article.id,
    )
    old_id = old_document.id

    old_document.deleted_at = datetime.now(UTC)
    db.flush()

    created = SearchIndexingService(
        repository=repository
    ).index_article(
        db,
        article,
    )
    db.flush()

    replacement = repository.get_by_article_id(
        db,
        article.id,
    )

    assert created is True
    assert replacement is not None
    assert replacement.id != old_id
    assert replacement.deleted_at is None


@pytest.mark.parametrize(
    "ineligible",
    [
        "article",
        "feed",
        "source",
    ],
)
def test_delete_ineligible_returns_deleted_article_ids(
    db,
    ineligible,
):
    article = create_indexed_article(db)

    if ineligible == "article":
        article.deleted_at = datetime.now(UTC)

    elif ineligible == "feed":
        article.feed.active = False

    else:
        article.feed.source.deleted_at = datetime.now(UTC)

    db.flush()

    deleted_ids = (
        SearchDocumentRepository()
        .delete_ineligible(db)
    )

    assert deleted_ids == [article.id]

    assert (
        SearchDocumentRepository()
        .get_by_article_id(
            db,
            article.id,
            include_deleted=True,
        )
        is None
    )


def test_delete_ineligible_hard_deletes_soft_deleted_document(db):
    article = create_indexed_article(db)
    repository = SearchDocumentRepository()

    document = repository.get_by_article_id(
        db,
        article.id,
    )
    document.deleted_at = datetime.now(UTC)
    db.flush()

    assert repository.delete_ineligible(
        db
    ) == [article.id]

    assert (
        repository.get_by_article_id(
            db,
            article.id,
            include_deleted=True,
        )
        is None
    )