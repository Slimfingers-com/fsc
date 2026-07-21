from datetime import UTC, datetime

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.ingestion.models import (
    FeedFetchResult,
    FeedFormat,
    ParsedFeed,
    ParsedFeedEntry,
)
from app.repositories.article import ArticleRepository
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.services.feed_persistence import FeedPersistenceService
from app.services.source import SourceService


def parsed_entry(**overrides):
    values = {
        "external_id": "article-1",
        "title": "Original title",
        "link": "https://example.com/articles/1",
        "summary": "Original summary",
        "content": "<p>Original content</p>",
        "author": "Jane Doe",
        "published_at": datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 7, 20, 11, 0, tzinfo=UTC),
        "categories": (),
        "enclosures": (),
    }
    values.update(overrides)
    return ParsedFeedEntry(**values)


def parsed_feed(*entries):
    return ParsedFeed(
        source_url="https://example.com/feed.xml",
        format=FeedFormat.RSS,
        version="rss20",
        title="Example feed",
        link="https://example.com",
        description="Example",
        language="en",
        updated_at=None,
        entries=tuple(entries),
        warnings=(),
    )


def create_feed(db):
    source = SourceService().create_source(
        db,
        SourceCreate(
            name="Example News",
            url="https://example.com",
            source_type=SourceType.NEWS,
            feeds=[
                FeedCreate(
                    name="Main Feed",
                    url="https://example.com/feed.xml",
                )
            ],
        ),
    )
    return source.feeds[0]


def test_persist_inserts_summary_and_content(db):
    feed = create_feed(db)
    result = FeedPersistenceService().persist(
        db,
        feed=feed,
        parsed_feed=parsed_feed(parsed_entry()),
        fetched_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
    )

    articles = ArticleRepository().list_by_feed(db, feed.id)
    assert result.inserted == 1
    assert result.updated == 0
    assert result.unchanged == 0
    assert len(articles) == 1
    assert articles[0].summary == "Original summary"
    assert articles[0].content == "<p>Original content</p>"
    assert articles[0].identity_type is ArticleIdentityType.GUID
    assert feed.last_success_at == datetime(2026, 7, 21, 8, 0, tzinfo=UTC)


def test_repeated_persist_is_idempotent(db):
    feed = create_feed(db)
    service = FeedPersistenceService()
    document = parsed_feed(parsed_entry())

    service.persist(db, feed=feed, parsed_feed=document)
    result = service.persist(db, feed=feed, parsed_feed=document)

    assert result.inserted == 0
    assert result.updated == 0
    assert result.unchanged == 1
    assert len(ArticleRepository().list_by_feed(db, feed.id)) == 1


def test_existing_article_is_updated(db):
    feed = create_feed(db)
    service = FeedPersistenceService()
    service.persist(db, feed=feed, parsed_feed=parsed_feed(parsed_entry()))

    result = service.persist(
        db,
        feed=feed,
        parsed_feed=parsed_feed(
            parsed_entry(
                title="Updated title",
                summary="Updated summary",
                content="<p>Updated content</p>",
            )
        ),
    )

    article = ArticleRepository().list_by_feed(db, feed.id)[0]
    assert result.updated == 1
    assert article.title == "Updated title"
    assert article.summary == "Updated summary"
    assert article.content == "<p>Updated content</p>"


def test_link_identity_is_upgraded_when_guid_appears(db):
    feed = create_feed(db)
    service = FeedPersistenceService()

    service.persist(
        db,
        feed=feed,
        parsed_feed=parsed_feed(parsed_entry(external_id=None)),
    )
    first = ArticleRepository().list_by_feed(db, feed.id)[0]
    original_id = first.id
    assert first.identity_type is ArticleIdentityType.LINK

    result = service.persist(
        db,
        feed=feed,
        parsed_feed=parsed_feed(parsed_entry(external_id="article-1")),
    )

    articles = ArticleRepository().list_by_feed(db, feed.id)
    assert result.inserted == 0
    assert result.updated == 1
    assert len(articles) == 1
    assert articles[0].id == original_id
    assert articles[0].identity_type is ArticleIdentityType.GUID
    assert articles[0].guid == "article-1"


def test_fetch_metadata_updates_feed(db):
    feed = create_feed(db)
    fetched_at = datetime(2026, 7, 21, 9, 0, tzinfo=UTC)
    fetch_result = FeedFetchResult(
        requested_url=feed.url,
        final_url=feed.url,
        status_code=200,
        content=b"feed",
        content_type="application/rss+xml",
        etag='"v2"',
        last_modified="Tue, 21 Jul 2026 09:00:00 GMT",
    )

    FeedPersistenceService().persist(
        db,
        feed=feed,
        parsed_feed=parsed_feed(),
        fetch_result=fetch_result,
        fetched_at=fetched_at,
    )

    assert feed.etag == '"v2"'
    assert feed.last_modified == "Tue, 21 Jul 2026 09:00:00 GMT"
    assert feed.last_fetched_at == fetched_at
    assert feed.last_success_at == fetched_at
    assert feed.last_error_at is None
    assert feed.last_error_message is None
