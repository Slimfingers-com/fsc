import logging

from app.core.settings import settings
from app.workers.search_reindex import SearchReindexWorker


def main() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker = SearchReindexWorker(
        poll_interval_seconds=settings.search_worker_poll_interval_seconds,
        batch_limit=settings.search_worker_batch_limit,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
