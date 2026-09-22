import logging

from app.clustering.rule_based import (
    RuleBasedStoryClusterer,
)
from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.story_clustering import (
    StoryClusteringRunner,
    StoryClusteringService,
)
from app.workers.story_clustering import (
    StoryClusteringWorker,
)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    clusterer = RuleBasedStoryClusterer(
        min_similarity=(
            settings.story_clustering_min_similarity
        ),
        semantic_similarity_threshold=(
            settings.story_clustering_semantic_similarity_threshold
        ),
    )

    service = StoryClusteringService(
        clusterer=clusterer,
    )

    runner = StoryClusteringRunner(
        SessionLocal,
        service,
        claim_ttl_seconds=(
            settings.story_clustering_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings.story_clustering_retry_base_seconds
        ),
        retry_max_seconds=(
            settings.story_clustering_retry_max_seconds
        ),
        window_hours=(
            settings.story_clustering_window_hours
        ),
        candidate_limit=(
            settings.story_clustering_candidate_limit
        ),
    )

    worker = StoryClusteringWorker(
        poll_interval_seconds=(
            settings.story_clustering_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings.story_clustering_worker_batch_limit
        ),
        runner=runner,
    )

    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
