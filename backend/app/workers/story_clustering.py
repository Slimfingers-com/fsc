import logging
import signal
import threading
from types import FrameType

from app.services.story_clustering import (
    StoryClusteringRunner,
)

logger = logging.getLogger(__name__)


class StoryClusteringWorker:
    def __init__(
        self,
        *,
        poll_interval_seconds: float,
        batch_limit: int,
        runner: StoryClusteringRunner,
        stop_event: threading.Event | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError(
                "poll_interval_seconds must be greater than zero"
            )

        if batch_limit <= 0:
            raise ValueError(
                "batch_limit must be greater than zero"
            )

        self.poll_interval_seconds = poll_interval_seconds
        self.batch_limit = batch_limit
        self.runner = runner
        self.stop_event = (
            stop_event
            or threading.Event()
        )

    def run_once(self):
        result = self.runner.run_pending(
            limit=self.batch_limit
        )

        logger.info(
            "Story clustering completed: "
            "selected=%s processed=%s skipped=%s failed=%s",
            result.selected,
            result.processed,
            result.skipped,
            result.failed,
        )

        return result

    def run_forever(self) -> None:
        logger.info(
            "Story clustering worker started"
        )

        while not self.stop_event.is_set():
            try:
                self.run_once()

            except Exception:
                logger.exception(
                    "Unexpected story clustering worker failure"
                )

            self.stop_event.wait(
                self.poll_interval_seconds
            )

        logger.info(
            "Story clustering worker stopped"
        )

    def request_stop(self) -> None:
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        def handle_signal(
            signum: int,
            frame: FrameType | None,
        ) -> None:
            logger.info(
                "Received signal %s; "
                "stopping story clustering worker",
                signum,
            )

            self.request_stop()

        signal.signal(
            signal.SIGTERM,
            handle_signal,
        )
        signal.signal(
            signal.SIGINT,
            handle_signal,
        )
