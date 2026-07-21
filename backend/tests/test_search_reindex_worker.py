import threading

import pytest

from app.services.search_indexing import SearchIndexBatchResult
from app.workers.search_reindex import SearchReindexWorker


class StubRunner:
    def __init__(self):
        self.calls = []

    def run_pending(self, *, limit):
        self.calls.append(limit)
        return SearchIndexBatchResult(processed=3, created=2, updated=1)


def test_worker_runs_reindex_batch():
    runner = StubRunner()
    worker = SearchReindexWorker(poll_interval_seconds=1, batch_limit=25, runner=runner)
    assert worker.run_once().processed == 3
    assert runner.calls == [25]


def test_worker_validates_configuration_and_stops():
    with pytest.raises(ValueError, match="batch_limit"):
        SearchReindexWorker(poll_interval_seconds=1, batch_limit=0, runner=StubRunner())
    event = threading.Event()
    worker = SearchReindexWorker(poll_interval_seconds=1, batch_limit=1, runner=StubRunner(), stop_event=event)
    worker.request_stop()
    assert event.is_set()
