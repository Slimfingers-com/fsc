import logging

from app.core.settings import settings
from app.workers.entity_topic import EntityTopicWorker


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    worker = EntityTopicWorker(poll_interval_seconds=settings.entity_topic_worker_poll_interval_seconds, batch_limit=settings.entity_topic_worker_batch_limit)
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
