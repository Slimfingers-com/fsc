import logging

from app.claims.rule_based import (
    RuleBasedClaimExtractor,
)
from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.claim_extraction import (
    ClaimExtractionRunner,
    ClaimExtractionService,
)
from app.workers.claim_extraction import (
    ClaimExtractionWorker,
)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    service = ClaimExtractionService(
        extractor=(
            RuleBasedClaimExtractor()
        ),
        min_confidence=(
            settings.claim_extraction_min_confidence
        ),
        max_claims=(
            settings.claim_extraction_max_claims_per_article
        ),
    )

    runner = ClaimExtractionRunner(
        SessionLocal,
        service,
        claim_ttl_seconds=(
            settings.claim_extraction_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings.claim_extraction_retry_base_seconds
        ),
        retry_max_seconds=(
            settings.claim_extraction_retry_max_seconds
        ),
    )

    worker = ClaimExtractionWorker(
        poll_interval_seconds=(
            settings.claim_extraction_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings.claim_extraction_worker_batch_limit
        ),
        runner=runner,
    )

    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
