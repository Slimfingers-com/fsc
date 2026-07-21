import logging

from app.core.settings import settings
from app.workers.entity_topic import EntityTopicWorker
from app.services.entity_topic_analysis import EntityTopicAnalysisRunner, EntityTopicAnalysisService
from app.db.session import SessionLocal


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    service = EntityTopicAnalysisService(min_entity_confidence=settings.entity_topic_min_entity_confidence, min_topic_confidence=settings.entity_topic_min_topic_confidence, max_topics=settings.entity_topic_max_topics_per_article)
    runner = EntityTopicAnalysisRunner(SessionLocal, service, claim_ttl_seconds=settings.entity_topic_worker_claim_ttl_seconds, retry_base_seconds=settings.entity_topic_retry_base_seconds, retry_max_seconds=settings.entity_topic_retry_max_seconds)
    worker = EntityTopicWorker(poll_interval_seconds=settings.entity_topic_worker_poll_interval_seconds, batch_limit=settings.entity_topic_worker_batch_limit, runner=runner)
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
