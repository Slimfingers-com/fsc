from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.search.builder import SearchDocumentBuilder


def test_builder_denormalizes_normalized_article():
    indexed_at = datetime(2026, 7, 21, tzinfo=UTC)
    source = Source(id=uuid4(), name="Example", normalized_name="example", slug="example")
    feed = Feed(id=uuid4(), source_id=source.id, source=source, name="Main", url="https://example.test/feed")
    article = Article(
        id=uuid4(), feed_id=feed.id, feed=feed, normalized_title="A title",
        normalized_text="The normalized body", content_hash="a" * 64,
        normalized_at=indexed_at, language_code="en", link="https://example.test/article",
    )
    result = SearchDocumentBuilder(clock=lambda: indexed_at).build(article)
    assert result.article_id == article.id
    assert result.source_slug == "example"
    assert result.title == "A title"
    assert result.body == "The normalized body"
    assert result.builder_version == SearchDocumentBuilder.VERSION
    assert result.indexed_at == indexed_at


def test_builder_rejects_unnormalized_article():
    with pytest.raises(ValueError, match="normalized"):
        SearchDocumentBuilder().build(Article())
