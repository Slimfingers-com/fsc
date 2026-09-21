import logging

from app.core.settings import settings
from app.db.session import SessionLocal
from app.perspectives.rule_based import (
    RuleBasedPerspectiveAnalyzer,
)
from app.services.perspective_analysis import (
    PerspectiveAnalysisRunner,
    PerspectiveAnalysisService,
)
from app.workers.perspective_analysis import (
    PerspectiveAnalysisWorker,
)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    service = PerspectiveAnalysisService(
        analyzer=(
            RuleBasedPerspectiveAnalyzer()
        ),
        min_confidence=(
            settings.perspective_analysis_min_confidence
        ),
    )

    runner = PerspectiveAnalysisRunner(
        SessionLocal,
        service,
        claim_ttl_seconds=(
            settings.perspective_analysis_worker_claim_ttl_seconds
        ),
        retry_base_seconds=(
            settings.perspective_analysis_retry_base_seconds
        ),
        retry_max_seconds=(
            settings.perspective_analysis_retry_max_seconds
        ),
    )

    worker = PerspectiveAnalysisWorker(
        poll_interval_seconds=(
            settings.perspective_analysis_worker_poll_interval_seconds
        ),
        batch_limit=(
            settings.perspective_analysis_worker_batch_limit
        ),
        runner=runner,
    )

    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
