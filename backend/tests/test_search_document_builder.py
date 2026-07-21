from datetime import UTC, datetime
from uuid import UUID, uuid4

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


def test_document_hash_covers_all_search_fields():
    article = _make_article()
    builder = SearchDocumentBuilder()
    original = builder.build(article).document_hash
    variants = []
    for field, value in (
        ("normalized_title", "Changed title"),
        ("normalized_text", "Changed body"),
        ("link", "https://example.test/changed"),
        ("language_code", "de"),
        ("published_at", datetime(2026, 7, 22, tzinfo=UTC)),
    ):
        variant = _make_article()
        setattr(variant, field, value)
        variants.append(variant)
    source_name = _make_article()
    source_name.feed.source.name = "Renamed"
    variants.append(source_name)
    source_slug = _make_article()
    source_slug.feed.source.slug = "renamed"
    variants.append(source_slug)
    source_id = _make_article()
    source_id.feed.source.id = uuid4()
    variants.append(source_id)
    assert all(builder.build(variant).document_hash != original for variant in variants)


def test_builder_rejects_unnormalized_article():
    with pytest.raises(ValueError, match="normalized"):
        SearchDocumentBuilder().build(Article())


def _make_article():
    indexed_at = datetime(2026, 7, 21, tzinfo=UTC)
    source = Source(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Example", normalized_name="example", slug="example",
    )
    feed = Feed(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        source_id=source.id, source=source, name="Main", url="https://example.test/feed",
    )
    return Article(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        feed_id=feed.id, feed=feed, normalized_title="A title",
        normalized_text="The normalized body", content_hash="a" * 64,
        normalized_at=indexed_at, language_code="en", link="https://example.test/article",
        published_at=indexed_at,
    )
