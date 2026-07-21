from datetime import UTC, datetime

from app.enums.source_type import SourceType
from app.ingestion.exceptions import FeedTimeoutError
from app.ingestion.models import FeedFetchResult, FeedFormat, ParsedFeed, ParsedFeedEntry
from app.repositories.article import ArticleRepository
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.services.feed_synchronization import (
    FeedSynchronizationService,
    FeedSynchronizationStatus,
)
from app.services.source import SourceService


class StubFetcher:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.request = None

    def fetch(self, request):
        self.request = request
        if self.error:
            raise self.error
        return self.result


class StubParser:
    def __init__(self, result):
        self.result = result
        self.called = False

    def parse(self, fetch_result):
        self.called = True
        return self.result


def create_feed(db):
    source = SourceService().create_source(
        db,
        SourceCreate(
            name="Synchronization News",
            url="https://sync.example.com",
            source_type=SourceType.NEWS,
            feeds=[FeedCreate(name="Main", url="https://sync.example.com/feed")],
        ),
    )
    return source.feeds[0]


def parsed_feed():
    return ParsedFeed(
        source_url="https://sync.example.com/feed",
        format=FeedFormat.RSS,
        version="rss20",
        title="Sync",
        link="https://sync.example.com",
        description=None,
        language="en",
        updated_at=None,
        entries=(
            ParsedFeedEntry(
                external_id="sync-1",
                title="Synchronized article",
                link="https://sync.example.com/1",
                summary="Summary",
                content="<p>Content</p>",
                author="Author",
                published_at=None,
                updated_at=None,
                categories=(),
                enclosures=(),
            ),
        ),
        warnings=(),
    )


def fetch_result(status_code=200, content=b"feed"):
    return FeedFetchResult(
        requested_url="https://sync.example.com/feed",
        final_url="https://sync.example.com/feed",
        status_code=status_code,
        content=content,
        content_type="application/rss+xml",
        etag='"v2"',
        last_modified="Tue, 21 Jul 2026 10:00:00 GMT",
    )


def test_synchronize_fetches_parses_and_persists(db):
    feed = create_feed(db)
    fetcher = StubFetcher(fetch_result())
    parser = StubParser(parsed_feed())
    now = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)

    result = FeedSynchronizationService(fetcher=fetcher, parser=parser).synchronize(
        db, feed=feed, synchronized_at=now
    )

    assert result.status is FeedSynchronizationStatus.SYNCHRONIZED
    assert result.inserted == 1
    assert parser.called
    assert fetcher.request.url == feed.url
    assert feed.last_success_at == now
    assert len(ArticleRepository().list_by_feed(db, feed.id)) == 1


def test_synchronize_sends_conditional_metadata(db):
    feed = create_feed(db)
    feed.etag = '"v1"'
    feed.last_modified = "Mon, 20 Jul 2026 10:00:00 GMT"
    fetcher = StubFetcher(fetch_result(status_code=304, content=None))
    parser = StubParser(parsed_feed())

    result = FeedSynchronizationService(fetcher=fetcher, parser=parser).synchronize(
        db, feed=feed
    )

    assert result.status is FeedSynchronizationStatus.NOT_MODIFIED
    assert fetcher.request.etag == '"v1"'
    assert fetcher.request.last_modified == "Mon, 20 Jul 2026 10:00:00 GMT"
    assert not parser.called
    assert feed.etag == '"v2"'
    assert feed.last_error_at is None


def test_ingestion_failure_is_recorded_without_hiding_previous_success(db):
    feed = create_feed(db)
    previous_success = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
    now = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
    feed.last_success_at = previous_success
    fetcher = StubFetcher(error=FeedTimeoutError("timed out"))

    result = FeedSynchronizationService(fetcher=fetcher).synchronize(
        db, feed=feed, synchronized_at=now
    )

    assert result.status is FeedSynchronizationStatus.FAILED
    assert result.error_message == "FeedTimeoutError: timed out"
    assert feed.last_fetched_at == now
    assert feed.last_error_at == now
    assert feed.last_success_at == previous_success
    assert feed.last_error_message == result.error_message
