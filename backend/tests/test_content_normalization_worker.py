import threading

from app.services.article_normalization import ArticleNormalizationBatchResult
from app.workers.content_normalization import ContentNormalizationWorker


class StubRunner:
    def __init__(self):
        self.calls = []

    def run_pending(self, *, limit):
        self.calls.append(limit)
        return ArticleNormalizationBatchResult(processed=2, changed=1, unchanged=1)


def test_worker_runs_batch():
    runner = StubRunner()
    worker = ContentNormalizationWorker(
        poll_interval_seconds=1,
        batch_limit=25,
        runner=runner,
    )
    result = worker.run_once()
    assert result.processed == 2
    assert runner.calls == [25]


def test_worker_validates_configuration():
    runner = StubRunner()
    try:
        ContentNormalizationWorker(poll_interval_seconds=0, batch_limit=1, runner=runner)
    except ValueError as error:
        assert "poll_interval_seconds" in str(error)
    else:
        raise AssertionError("ValueError expected")


def test_request_stop_sets_event():
    event = threading.Event()
    worker = ContentNormalizationWorker(
        poll_interval_seconds=1,
        batch_limit=1,
        runner=StubRunner(),
        stop_event=event,
    )
    worker.request_stop()
    assert event.is_set()
