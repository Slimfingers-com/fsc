import logging
import signal
import threading
from types import FrameType

from app.db.session import SessionLocal
from app.services.entity_topic_analysis import EntityTopicAnalysisRunner

logger = logging.getLogger(__name__)


class EntityTopicWorker:
    def __init__(self, *, poll_interval_seconds: float, batch_limit: int, runner: EntityTopicAnalysisRunner | None = None, stop_event: threading.Event | None = None) -> None:
        if poll_interval_seconds <= 0 or batch_limit <= 0:
            raise ValueError("poll interval and batch limit must be greater than zero")
        self.poll_interval_seconds, self.batch_limit = poll_interval_seconds, batch_limit
        self.runner = runner or EntityTopicAnalysisRunner(SessionLocal)
        self.stop_event = stop_event or threading.Event()

    def run_once(self):
        result = self.runner.run_pending(limit=self.batch_limit)
        logger.info("Entity/topic analysis completed: selected=%s processed=%s skipped=%s failed=%s", result.selected, result.processed, result.skipped, result.failed)
        return result

    def run_forever(self) -> None:
        logger.info("Entity/topic worker started")
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Unexpected entity/topic worker failure")
            self.stop_event.wait(self.poll_interval_seconds)
        logger.info("Entity/topic worker stopped")

    def request_stop(self) -> None:
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        def handler(signum: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s; stopping entity/topic worker", signum)
            self.request_stop()
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
