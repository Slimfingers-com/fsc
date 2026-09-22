import logging

from app.consensus.rule_based import RuleBasedConsensusAnalyzer
from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.consensus import ConsensusRunner, ConsensusService
from app.workers.consensus import ConsensusWorker


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    runner = ConsensusRunner(
        SessionLocal,
        ConsensusService(
            analyzer=RuleBasedConsensusAnalyzer(
                minimum_independent_sources=(
                    settings.consensus_minimum_independent_sources
                )
            )
        ),
        claim_ttl_seconds=settings.consensus_worker_claim_ttl_seconds,
        retry_base_seconds=settings.consensus_retry_base_seconds,
        retry_max_seconds=settings.consensus_retry_max_seconds,
    )
    worker = ConsensusWorker(
        poll_interval_seconds=settings.consensus_worker_poll_interval_seconds,
        batch_limit=settings.consensus_worker_batch_limit,
        runner=runner,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
