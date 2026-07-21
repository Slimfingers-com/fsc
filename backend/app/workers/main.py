import logging

from app.core.settings import settings
from app.workers.feed_ingestion import FeedIngestionWorker


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    worker = FeedIngestionWorker(
        poll_interval_seconds=settings.feed_worker_poll_interval_seconds,
        batch_limit=settings.feed_worker_batch_limit,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
