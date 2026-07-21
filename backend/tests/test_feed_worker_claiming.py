from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Lock
from uuid import uuid4

from sqlalchemy import delete, select

from app.enums.source_type import SourceType
from app.ingestion.models import FeedFormat, ParsedFeed, ParsedFeedEntry
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.feed import FeedRepository
from app.services.feed_persistence import FeedPersistenceService
from app.services.feed_synchronization import (
    FeedSynchronizationResult,
    FeedSynchronizationRunner,
    FeedSynchronizationStatus,
)
from tests.conftest import TestSessionLocal


def _committed_feeds(count: int) -> tuple[list, object]:
    token = uuid4().hex
    with TestSessionLocal.begin() as db:
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=f"https://{token}.test",
            source_type=SourceType.NEWS,
        )
        feeds = [
            Feed(source=source, name=f"Feed {index}", url=f"https://{token}.test/{index}")
            for index in range(count)
        ]
        db.add_all(feeds)
        db.flush()
        return [feed.id for feed in feeds], source.id


def _cleanup_source(source_id) -> None:
    with TestSessionLocal.begin() as db:
        db.execute(delete(Source).where(Source.id == source_id))


class RecordingSynchronizationService:
    def __init__(self) -> None:
        self.feed_ids = []
        self.lock = Lock()

    def synchronize(self, db, *, feed, synchronized_at):
        with self.lock:
            self.feed_ids.append(feed.id)
        feed.last_fetched_at = synchronized_at
        return FeedSynchronizationResult(
            feed_id=feed.id,
            status=FeedSynchronizationStatus.NOT_MODIFIED,
        )


def test_two_parallel_feed_workers_process_each_feed_once():
    feed_ids, source_id = _committed_feeds(6)
    service = RecordingSynchronizationService()
    now = datetime.now(UTC)
    runners = [
        FeedSynchronizationRunner(
            TestSessionLocal,
            synchronization_service=service,
            worker_id=f"worker-{index}",
            clock=lambda: now,
        )
        for index in range(2)
    ]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda runner: runner.run_due(limit=6), runners))
        assert sum(result.processed for result in results) == 6
        assert set(service.feed_ids) == set(feed_ids)
        assert len(service.feed_ids) == len(set(service.feed_ids))
        with TestSessionLocal() as db:
            feeds = list(db.scalars(select(Feed).where(Feed.id.in_(feed_ids))))
            assert all(feed.claimed_by is None for feed in feeds)
    finally:
        _cleanup_source(source_id)


def test_feed_claim_skips_row_locked_by_another_transaction():
    feed_ids, source_id = _committed_feeds(3)
    repository = FeedRepository()
    now = datetime.now(UTC)
    first = TestSessionLocal()
    second = TestSessionLocal()
    try:
        first.begin()
        first.scalar(select(Feed).where(Feed.id == feed_ids[0]).with_for_update())
        with second.begin():
            claimed = repository.claim_due_active(
                second,
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                claimed_by="second",
                limit=3,
            )
        assert feed_ids[0] not in claimed
        assert set(claimed) == set(feed_ids[1:])
    finally:
        first.rollback()
        first.close()
        second.close()
        _cleanup_source(source_id)


def test_expired_feed_lease_can_be_reclaimed():
    feed_ids, source_id = _committed_feeds(1)
    now = datetime.now(UTC)
    try:
        with TestSessionLocal.begin() as db:
            feed = db.get(Feed, feed_ids[0])
            feed.claimed_at = now - timedelta(minutes=10)
            feed.claimed_by = "dead-worker"
            feed.claim_expires_at = now - timedelta(minutes=5)
        with TestSessionLocal.begin() as db:
            claimed = FeedRepository().claim_due_active(
                db,
                now=now,
                claim_expires_at=now + timedelta(minutes=5),
                claimed_by="replacement",
                limit=1,
            )
        assert claimed == feed_ids
    finally:
        _cleanup_source(source_id)


def _article_document(token: str) -> ParsedFeed:
    return ParsedFeed(
        source_url=f"https://{token}.test/feed",
        format=FeedFormat.RSS,
        version="rss20",
        title="Concurrent feed",
        link=f"https://{token}.test",
        description=None,
        language="en",
        updated_at=None,
        entries=(
            ParsedFeedEntry(
                external_id="shared-guid",
                title="Shared article",
                link=f"https://{token}.test/article",
                summary=None,
                content="body",
                author=None,
                published_at=None,
                updated_at=None,
                categories=(),
                enclosures=(),
            ),
        ),
        warnings=(),
    )


def test_concurrent_article_insert_reloads_conflicting_row():
    feed_ids, source_id = _committed_feeds(1)
    token = uuid4().hex
    document = _article_document(token)
    barrier = Barrier(2)

    def persist():
        with TestSessionLocal.begin() as db:
            feed = db.get(Feed, feed_ids[0])
            barrier.wait()
            return FeedPersistenceService().persist(
                db, feed=feed, parsed_feed=document
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: persist(), range(2)))
        assert sum(result.inserted for result in results) == 1
        assert sum(result.unchanged for result in results) == 1
        with TestSessionLocal() as db:
            articles = list(
                db.scalars(select(Article).where(Article.feed_id == feed_ids[0]))
            )
            assert len(articles) == 1
    finally:
        _cleanup_source(source_id)
