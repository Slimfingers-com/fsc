import logging
import signal
import threading
from types import FrameType

from app.db.session import SessionLocal
from app.services.search_indexing import SearchIndexingRunner

logger = logging.getLogger(__name__)


class SearchReindexWorker:
    def __init__(self, *, poll_interval_seconds: float, batch_limit: int, runner: SearchIndexingRunner | None = None, stop_event: threading.Event | None = None) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if batch_limit <= 0:
            raise ValueError("batch_limit must be greater than zero")
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_limit = batch_limit
        self.runner = runner or SearchIndexingRunner(SessionLocal)
        self.stop_event = stop_event or threading.Event()

    def run_once(self):
        result = self.runner.run_pending(limit=self.batch_limit)
        logger.info("Search reindex completed: processed=%s created=%s updated=%s", result.processed, result.created, result.updated)
        return result

    def run_forever(self) -> None:
        logger.info("Search reindex worker started")
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Unexpected search reindex worker failure")
            self.stop_event.wait(self.poll_interval_seconds)
        logger.info("Search reindex worker stopped")

    def request_stop(self) -> None:
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        def handle_signal(signum: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s; stopping search reindex worker", signum)
            self.request_stop()
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
