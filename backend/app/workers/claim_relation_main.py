import logging

from app.claim_relations.rule_based import (
    RuleBasedClaimRelationAnalyzer,
)
from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.claim_relations import (
    ClaimRelationRunner,
    ClaimRelationService,
)
from app.workers.claim_relations import (
    ClaimRelationWorker,
)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    analyzer = (
        RuleBasedClaimRelationAnalyzer(
            group_similarity_threshold=(
                settings
                .claim_relation_group_similarity_threshold
            ),
            contradiction_similarity_threshold=(
                settings
                .claim_relation_contradiction_similarity_threshold
            ),
        )
    )

    runner = ClaimRelationRunner(
        SessionLocal,
        ClaimRelationService(
            analyzer=analyzer
        ),
        claim_ttl_seconds=(
            settings
            .claim_relation_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings
            .claim_relation_retry_base_seconds
        ),
        retry_max_seconds=(
            settings
            .claim_relation_retry_max_seconds
        ),
    )

    worker = ClaimRelationWorker(
        poll_interval_seconds=(
            settings
            .claim_relation_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings
            .claim_relation_worker_batch_limit
        ),
        runner=runner,
    )

    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
