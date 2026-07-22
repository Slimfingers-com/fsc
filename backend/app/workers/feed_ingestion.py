from __future__ import annotations

import logging
import signal
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from types import FrameType
from typing import Callable

from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.feed_synchronization import (
    FeedSynchronizationBatchResult,
    FeedSynchronizationRunner,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerRunResult:
    started_at: datetime
    finished_at: datetime
    batch: FeedSynchronizationBatchResult


class FeedIngestionWorker:
    """Long-running polling worker for due feed synchronization."""

    def __init__(
        self,
        *,
        poll_interval_seconds: float,
        batch_limit: int,
        runner: FeedSynchronizationRunner | None = None,
        stop_event: threading.Event | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if batch_limit <= 0:
            raise ValueError("batch_limit must be greater than zero")

        self.poll_interval_seconds = poll_interval_seconds
        self.batch_limit = batch_limit
        self.runner = runner or FeedSynchronizationRunner(
            SessionLocal,
            claim_ttl_seconds=settings.feed_worker_claim_ttl_seconds,
        )
        self.stop_event = stop_event or threading.Event()
        self.clock = clock or (lambda: datetime.now(UTC))

    def run_once(self) -> WorkerRunResult:
        started_at = self.clock()
        batch = self.runner.run_due(now=started_at, limit=self.batch_limit)
        finished_at = self.clock()
        result = WorkerRunResult(
            started_at=started_at,
            finished_at=finished_at,
            batch=batch,
        )
        logger.info(
            "Feed ingestion run completed: processed=%s synchronized=%s "
            "not_modified=%s failed=%s",
            batch.processed,
            batch.synchronized,
            batch.not_modified,
            batch.failed,
        )
        return result

    def run_forever(self) -> None:
        logger.info(
            "Feed ingestion worker started: poll_interval_seconds=%s batch_limit=%s",
            self.poll_interval_seconds,
            self.batch_limit,
        )
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Unexpected feed ingestion worker failure")
            self.stop_event.wait(self.poll_interval_seconds)
        logger.info("Feed ingestion worker stopped")

    def request_stop(self) -> None:
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        def handle_signal(signum: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s; stopping feed ingestion worker", signum)
            self.request_stop()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
