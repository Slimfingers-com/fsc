import logging

from app.consensus.rule_based import (
    RuleBasedConsensusAnalyzer,
)
from app.core.settings import settings
from app.coverage.rule_based import (
    RuleBasedCoverageAnalyzer,
)
from app.db.session import SessionLocal
from app.services.consensus import ConsensusService
from app.services.coverage import (
    CoverageRunner,
    CoverageService,
)
from app.workers.coverage import CoverageWorker


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    consensus_service = ConsensusService(
        analyzer=RuleBasedConsensusAnalyzer(
            minimum_independent_sources=(
                settings
                .consensus_minimum_independent_sources
            )
        )
    )
    service = CoverageService(
        analyzer=RuleBasedCoverageAnalyzer(
            minimum_independent_content_sources=(
                settings
                .coverage_minimum_independent_content_sources
            )
        ),
        consensus_service=consensus_service,
    )
    runner = CoverageRunner(
        SessionLocal,
        service,
        claim_ttl_seconds=(
            settings
            .coverage_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings
            .coverage_retry_base_seconds
        ),
        retry_max_seconds=(
            settings
            .coverage_retry_max_seconds
        ),
    )
    worker = CoverageWorker(
        poll_interval_seconds=(
            settings
            .coverage_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings
            .coverage_worker_batch_limit
        ),
        runner=runner,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
