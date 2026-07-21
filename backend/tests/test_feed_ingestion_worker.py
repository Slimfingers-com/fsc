from datetime import UTC, datetime, timedelta
from threading import Event

import pytest

from app.services.feed_synchronization import FeedSynchronizationBatchResult
from app.workers.feed_ingestion import FeedIngestionWorker


class StubRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, int]] = []

    def run_due(self, *, now: datetime, limit: int) -> FeedSynchronizationBatchResult:
        self.calls.append((now, limit))
        return FeedSynchronizationBatchResult(
            processed=3,
            synchronized=2,
            not_modified=1,
            failed=0,
        )


class FailingRunner:
    def __init__(self, stop_event: Event) -> None:
        self.stop_event = stop_event
        self.calls = 0

    def run_due(self, *, now: datetime, limit: int) -> FeedSynchronizationBatchResult:
        self.calls += 1
        self.stop_event.set()
        raise RuntimeError("boom")


def test_run_once_uses_configured_limit_and_returns_timestamps() -> None:
    runner = StubRunner()
    first = datetime(2026, 7, 21, 9, 0, tzinfo=UTC)
    second = first + timedelta(seconds=2)
    times = iter([first, second])
    worker = FeedIngestionWorker(
        poll_interval_seconds=60,
        batch_limit=25,
        runner=runner,
        clock=lambda: next(times),
    )

    result = worker.run_once()

    assert runner.calls == [(first, 25)]
    assert result.started_at == first
    assert result.finished_at == second
    assert result.batch.processed == 3


def test_constructor_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        FeedIngestionWorker(poll_interval_seconds=0, batch_limit=1)
    with pytest.raises(ValueError):
        FeedIngestionWorker(poll_interval_seconds=1, batch_limit=0)


def test_run_forever_survives_unexpected_run_failure() -> None:
    stop_event = Event()
    runner = FailingRunner(stop_event)
    worker = FeedIngestionWorker(
        poll_interval_seconds=0.01,
        batch_limit=10,
        runner=runner,
        stop_event=stop_event,
    )

    worker.run_forever()

    assert runner.calls == 1


def test_request_stop_sets_stop_event() -> None:
    worker = FeedIngestionWorker(poll_interval_seconds=1, batch_limit=1)
    assert not worker.stop_event.is_set()
    worker.request_stop()
    assert worker.stop_event.is_set()
