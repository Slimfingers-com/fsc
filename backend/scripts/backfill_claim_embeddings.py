from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import settings
from app.db.session import SessionLocal
from app.semantic.provider import OpenAIEmbeddingProvider
from app.services.semantic_embedding import (
    SemanticEmbeddingRunner,
    SemanticEmbeddingService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist one bounded claim-only embedding batch."
    )
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument(
        "--dimensions",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--model",
        default="text-embedding-3-small",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    provider = OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=args.model,
        dimensions=args.dimensions,
        timeout_seconds=settings.semantic_embedding_timeout_seconds,
    )
    service = SemanticEmbeddingService(
        provider=provider,
        max_article_characters=settings.semantic_embedding_max_article_characters,
        include_article_embeddings=False,
    )
    runner = SemanticEmbeddingRunner(
        SessionLocal,
        service,
        claim_ttl_seconds=settings.semantic_embedding_worker_claim_ttl_seconds,
        retry_base_seconds=settings.semantic_embedding_retry_base_seconds,
        retry_max_seconds=settings.semantic_embedding_retry_max_seconds,
    )
    result = runner.run_pending(limit=args.limit)
    print(
        {
            "selected": result.selected,
            "processed": result.processed,
            "skipped": result.skipped,
            "failed": result.failed,
            "model": args.model,
            "dimensions": args.dimensions,
            "article_embeddings": False,
        }
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
