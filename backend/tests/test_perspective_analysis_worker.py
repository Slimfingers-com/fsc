import threading

import pytest

from app.services.perspective_analysis import (
    PerspectiveAnalysisBatchResult,
)
from app.workers.perspective_analysis import (
    PerspectiveAnalysisWorker,
)


class StubRunner:
    def __init__(
        self,
    ):
        self.calls = []

    def run_pending(
        self,
        *,
        limit,
    ):
        self.calls.append(
            limit
        )
        return PerspectiveAnalysisBatchResult(
            selected=4,
            processed=2,
            skipped=1,
            failed=1,
        )


def test_worker_runs_perspective_batch():
    runner = StubRunner()
    worker = PerspectiveAnalysisWorker(
        poll_interval_seconds=1,
        batch_limit=25,
        runner=runner,
    )

    result = worker.run_once()

    assert (
        result.selected,
        result.processed,
        result.skipped,
        result.failed,
    ) == (
        4,
        2,
        1,
        1,
    )
    assert runner.calls == [
        25
    ]


@pytest.mark.parametrize(
    (
        "poll_interval_seconds",
        "batch_limit",
    ),
    (
        (0, 1),
        (1, 0),
    ),
)
def test_worker_validates_configuration(
    poll_interval_seconds,
    batch_limit,
):
    with pytest.raises(
        ValueError
    ):
        PerspectiveAnalysisWorker(
            poll_interval_seconds=(
                poll_interval_seconds
            ),
            batch_limit=(
                batch_limit
            ),
            runner=StubRunner(),
        )


def test_worker_request_stop_sets_event():
    event = threading.Event()
    worker = PerspectiveAnalysisWorker(
        poll_interval_seconds=1,
        batch_limit=1,
        runner=StubRunner(),
        stop_event=event,
    )

    worker.request_stop()

    assert event.is_set()
