import logging

from app.core.settings import settings
from app.db.session import SessionLocal
from app.semantic.provider import OpenAIEmbeddingProvider
from app.services.semantic_embedding import (
    SemanticEmbeddingRunner,
    SemanticEmbeddingService,
)
from app.workers.semantic_embedding import SemanticEmbeddingWorker


def main() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    runner = None
    if settings.semantic_embedding_enabled:
        if not settings.openai_api_key:
            raise RuntimeError(
                "SEMANTIC_EMBEDDING_ENABLED requires OPENAI_API_KEY"
            )

        provider = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.semantic_embedding_model,
            timeout_seconds=(
                settings.semantic_embedding_timeout_seconds
            ),
        )
        service = SemanticEmbeddingService(
            provider=provider,
            max_article_characters=(
                settings.semantic_embedding_max_article_characters
            ),
        )
        runner = SemanticEmbeddingRunner(
            SessionLocal,
            service,
            claim_ttl_seconds=(
                settings.semantic_embedding_worker_claim_ttl_seconds
            ),
            retry_base_seconds=(
                settings.semantic_embedding_retry_base_seconds
            ),
            retry_max_seconds=(
                settings.semantic_embedding_retry_max_seconds
            ),
        )

    worker = SemanticEmbeddingWorker(
        poll_interval_seconds=(
            settings.semantic_embedding_worker_poll_interval_seconds
        ),
        batch_limit=settings.semantic_embedding_worker_batch_limit,
        runner=runner,
    )
    worker.install_signal_handlers()
    worker.run_forever()


if __name__ == "__main__":
    main()
