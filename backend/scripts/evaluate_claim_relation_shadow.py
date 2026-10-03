from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.claim_relations.hybrid import HybridClaimRelationAnalyzer
from app.claim_relations.openai_provider import (
    OpenAISemanticClaimRelationProvider,
)
from app.claim_relations.rule_based import RuleBasedClaimRelationAnalyzer
from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.claim_relations import ClaimRelationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Luna claim-relation classifications in shadow mode. "
            "This command never persists claim relations."
        )
    )
    parser.add_argument(
        "--story-limit",
        type=int,
        default=100,
        help="maximum recent multi-source stories to inspect",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSONL output path",
    )
    return parser.parse_args()


def candidate_story_ids(limit: int) -> tuple[UUID, ...]:
    if limit <= 0:
        raise ValueError("story limit must be greater than zero")

    query = text(
        """
        select s.id
        from stories s
        join story_articles sa
          on sa.story_id = s.id
         and sa.deleted_at is null
        join articles a
          on a.id = sa.article_id
         and a.deleted_at is null
        join feeds f
          on f.id = a.feed_id
         and f.deleted_at is null
        join sources src
          on src.id = f.source_id
         and src.deleted_at is null
        where s.deleted_at is null
          and f.active is true
          and src.active is true
          and exists (
            select 1
            from story_claim_groups scg
            where scg.story_id = s.id
              and scg.deleted_at is null
          )
        group by s.id
        having count(distinct src.id) >= 2
        order by max(sa.article_time) desc, s.id
        limit :limit
        """
    )
    with SessionLocal() as db:
        return tuple(
            db.scalars(query, {"limit": limit}).all()
        )


def main() -> None:
    args = parse_args()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for Luna shadow evaluation"
        )

    provider = OpenAISemanticClaimRelationProvider(
        api_key=settings.openai_api_key,
        model=settings.claim_relation_openai_model,
        base_url=settings.claim_relation_openai_base_url,
        timeout_seconds=settings.claim_relation_openai_timeout_seconds,
        reasoning_effort=(
            settings.claim_relation_openai_reasoning_effort
        ),
        max_output_tokens=(
            settings.claim_relation_openai_max_output_tokens
        ),
    )
    hybrid = HybridClaimRelationAnalyzer(
        base_analyzer=RuleBasedClaimRelationAnalyzer(
            group_similarity_threshold=(
                settings.claim_relation_group_similarity_threshold
            ),
            contradiction_similarity_threshold=(
                settings.claim_relation_contradiction_similarity_threshold
            ),
        ),
        semantic_provider=provider,
        candidate_similarity_threshold=(
            settings
            .claim_relation_shadow_candidate_similarity_threshold
        ),
        max_semantic_candidates=(
            settings
            .claim_relation_shadow_max_candidates_per_story
        ),
    )
    service = ClaimRelationService(analyzer=hybrid)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    relation_counts: Counter[str] = Counter()
    stories_considered = 0
    stories_with_candidates = 0
    candidate_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    evaluated_at = datetime.now(UTC).isoformat()

    with args.output.open("w", encoding="utf-8") as output:
        with SessionLocal() as db:
            for story_id in candidate_story_ids(args.story_limit):
                stories_considered += 1
                snapshot = service.load_snapshot(
                    db,
                    story_id=story_id,
                )
                if snapshot is None:
                    continue

                prepared = service.prepare(snapshot)
                base = hybrid.base_analyzer.analyze(
                    prepared.analysis_input
                )
                candidates = hybrid.semantic_candidates(
                    prepared.analysis_input,
                    base,
                )
                if not candidates:
                    continue

                stories_with_candidates += 1
                decisions = provider.classify(candidates)
                hybrid.validate_decisions(
                    candidates,
                    decisions,
                )
                candidate_count += len(candidates)

                usage = provider.last_usage
                if usage is not None:
                    total_input_tokens += usage.input_tokens
                    total_output_tokens += usage.output_tokens

                candidate_by_pair = {
                    tuple(
                        sorted(
                            (
                                item.left_group_key,
                                item.right_group_key,
                            )
                        )
                    ): item
                    for item in candidates
                }

                for decision in decisions:
                    pair = tuple(
                        sorted(
                            (
                                decision.left_group_key,
                                decision.right_group_key,
                            )
                        )
                    )
                    candidate = candidate_by_pair[pair]
                    relation_counts[
                        decision.relation_kind.value
                    ] += 1

                    record = {
                        "shadow_only": True,
                        "evaluated_at": evaluated_at,
                        "model": provider.model,
                        "story_id": str(story_id),
                        "language_code": candidate.language_code,
                        "left_group_key": (
                            candidate.left_group_key
                        ),
                        "right_group_key": (
                            candidate.right_group_key
                        ),
                        "candidate_score": (
                            candidate.candidate_score
                        ),
                        "relation_kind": (
                            decision.relation_kind.value
                        ),
                        "confidence": decision.confidence,
                        "reason": decision.reason,
                        "left": {
                            "claim_id": str(
                                candidate.left_claim.claim_id
                            ),
                            "article_id": str(
                                candidate.left_claim.article_id
                            ),
                            "source_id": str(
                                candidate.left_claim.source_id
                            ),
                            "claim": (
                                candidate.left_claim.claim_text
                            ),
                            "title": (
                                candidate.left_claim.article_title
                            ),
                            "context": (
                                candidate.left_claim.article_context
                            ),
                        },
                        "right": {
                            "claim_id": str(
                                candidate.right_claim.claim_id
                            ),
                            "article_id": str(
                                candidate.right_claim.article_id
                            ),
                            "source_id": str(
                                candidate.right_claim.source_id
                            ),
                            "claim": (
                                candidate.right_claim.claim_text
                            ),
                            "title": (
                                candidate.right_claim.article_title
                            ),
                            "context": (
                                candidate.right_claim.article_context
                            ),
                        },
                    }
                    output.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )

    summary = {
        "shadow_only": True,
        "model": provider.model,
        "output": str(args.output),
        "stories_considered": stories_considered,
        "stories_with_candidates": stories_with_candidates,
        "candidate_count": candidate_count,
        "relation_counts": dict(
            sorted(relation_counts.items())
        ),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
    }
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
