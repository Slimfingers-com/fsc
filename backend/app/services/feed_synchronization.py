from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.ingestion import (
    FeedFetchRequest,
    FeedFetcher,
    FeedParser,
    IngestionError,
)
from app.models.feed import Feed
from app.repositories.feed import FeedRepository
from app.services.feed_persistence import FeedPersistenceResult, FeedPersistenceService


class FeedSynchronizationStatus(str, Enum):
    SYNCHRONIZED = "synchronized"
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FeedSynchronizationResult:
    feed_id: UUID
    status: FeedSynchronizationStatus
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    error_message: str | None = None


class FeedSynchronizationService:
    """Synchronize one feed inside the caller-controlled transaction."""

    def __init__(
        self,
        *,
        fetcher: FeedFetcher | None = None,
        parser: FeedParser | None = None,
        persistence_service: FeedPersistenceService | None = None,
        feed_repository: FeedRepository | None = None,
    ) -> None:
        self.fetcher = fetcher or FeedFetcher()
        self.parser = parser or FeedParser()
        self.persistence_service = persistence_service or FeedPersistenceService()
        self.feed_repository = feed_repository or FeedRepository()

    def synchronize(
        self,
        db: Session,
        *,
        feed: Feed,
        synchronized_at: datetime | None = None,
    ) -> FeedSynchronizationResult:
        now = synchronized_at or datetime.now(UTC)
        try:
            fetch_result = self.fetcher.fetch(
                FeedFetchRequest(
                    url=feed.url,
                    etag=feed.etag,
                    last_modified=feed.last_modified,
                )
            )

            if fetch_result.not_modified:
                self._mark_success(feed, now, fetch_result.etag, fetch_result.last_modified)
                self.feed_repository.flush(db)
                return FeedSynchronizationResult(
                    feed_id=feed.id,
                    status=FeedSynchronizationStatus.NOT_MODIFIED,
                )

            parsed_feed = self.parser.parse(fetch_result)
            persisted = self.persistence_service.persist(
                db,
                feed=feed,
                parsed_feed=parsed_feed,
                fetch_result=fetch_result,
                fetched_at=now,
            )
            return self._success_result(feed.id, persisted)
        except IngestionError as exc:
            message = self._error_message(exc)
            feed.last_fetched_at = now
            feed.last_error_at = now
            feed.last_error_message = message
            self.feed_repository.flush(db)
            return FeedSynchronizationResult(
                feed_id=feed.id,
                status=FeedSynchronizationStatus.FAILED,
                error_message=message,
            )

    @staticmethod
    def _mark_success(
        feed: Feed,
        now: datetime,
        etag: str | None,
        last_modified: str | None,
    ) -> None:
        feed.last_fetched_at = now
        feed.last_success_at = now
        feed.last_error_at = None
        feed.last_error_message = None
        feed.etag = etag
        feed.last_modified = last_modified

    @staticmethod
    def _success_result(
        feed_id: UUID,
        persisted: FeedPersistenceResult,
    ) -> FeedSynchronizationResult:
        return FeedSynchronizationResult(
            feed_id=feed_id,
            status=FeedSynchronizationStatus.SYNCHRONIZED,
            inserted=persisted.inserted,
            updated=persisted.updated,
            unchanged=persisted.unchanged,
        )

    @staticmethod
    def _error_message(exc: IngestionError) -> str:
        message = f"{type(exc).__name__}: {exc}"
        return message[:4000]


@dataclass(frozen=True, slots=True)
class FeedSynchronizationBatchResult:
    processed: int
    synchronized: int
    not_modified: int
    failed: int


class FeedSynchronizationRunner:
    """Process due feeds with one committed transaction per feed."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        feed_repository: FeedRepository | None = None,
        synchronization_service: FeedSynchronizationService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.feed_repository = feed_repository or FeedRepository()
        self.synchronization_service = (
            synchronization_service or FeedSynchronizationService()
        )

    def run_due(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> FeedSynchronizationBatchResult:
        run_at = now or datetime.now(UTC)
        with self.session_factory() as discovery_db:
            feed_ids = [
                feed.id
                for feed in self.feed_repository.list_due_active(
                    discovery_db,
                    now=run_at,
                    limit=limit,
                )
            ]

        results: list[FeedSynchronizationResult] = []
        for feed_id in feed_ids:
            with self.session_factory() as db:
                try:
                    feed = self.feed_repository.get_by_id(db, feed_id)
                    if feed is None or not feed.active:
                        continue
                    result = self.synchronization_service.synchronize(
                        db,
                        feed=feed,
                        synchronized_at=run_at,
                    )
                    db.commit()
                    results.append(result)
                except Exception:
                    db.rollback()
                    raise

        return FeedSynchronizationBatchResult(
            processed=len(results),
            synchronized=sum(
                result.status is FeedSynchronizationStatus.SYNCHRONIZED
                for result in results
            ),
            not_modified=sum(
                result.status is FeedSynchronizationStatus.NOT_MODIFIED
                for result in results
            ),
            failed=sum(
                result.status is FeedSynchronizationStatus.FAILED
                for result in results
            ),
        )
