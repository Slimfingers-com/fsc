import logging

from app.core.settings import settings
from app.db.session import SessionLocal
from app.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.services.evidence import EvidenceRunner, EvidenceService
from app.workers.evidence import EvidenceWorker


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    runner = EvidenceRunner(
        SessionLocal,
        EvidenceService(
            analyzer=RuleBasedEvidenceAnalyzer()
        ),
        claim_ttl_seconds=(
            settings.evidence_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings.evidence_retry_base_seconds
        ),
        retry_max_seconds=(
            settings.evidence_retry_max_seconds
        ),
    )

    worker = EvidenceWorker(
        poll_interval_seconds=(
            settings.evidence_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings.evidence_worker_batch_limit
        ),
        runner=runner,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
