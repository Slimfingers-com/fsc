import threading

import pytest

from app.services.claim_extraction import (
    ClaimExtractionBatchResult,
)
from app.workers.claim_extraction import (
    ClaimExtractionWorker,
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
        return ClaimExtractionBatchResult(
            selected=4,
            processed=2,
            skipped=1,
            failed=1,
        )


def test_worker_runs_claim_batch():
    runner = StubRunner()
    worker = ClaimExtractionWorker(
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
        ClaimExtractionWorker(
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
    worker = ClaimExtractionWorker(
        poll_interval_seconds=1,
        batch_limit=1,
        runner=StubRunner(),
        stop_event=event,
    )

    worker.request_stop()

    assert event.is_set()
