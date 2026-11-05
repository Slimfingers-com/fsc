"""Bounded, idempotent staged catch-up for current multi-source analysis.

Run only as a scheduled one-shot job; do not deploy Evidence, Consensus,
and Coverage as concurrent permanent workers on the 4-GB production host.
Each stage uses the existing atomic StoryProcessingRepository claim gate.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from uuid import UUID

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.claim_relations.rule_based import RuleBasedClaimRelationAnalyzer
from app.consensus.rule_based import RuleBasedConsensusAnalyzer
from app.core.settings import settings
from app.coverage.rule_based import RuleBasedCoverageAnalyzer
from app.db.session import SessionLocal
from app.enums.story_pipeline import StoryPipeline
from app.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.services.claim_relations import ClaimRelationRunner, ClaimRelationService
from app.services.consensus import ConsensusRunner, ConsensusService
from app.services.coverage import CoverageRunner, CoverageService
from app.services.evidence import EvidenceRunner, EvidenceService
from app.services.story_analysis import StoryAnalysisService


def choose_targets(missing: list[UUID], limit: int) -> list[UUID]:
    """Reserve 80% for newest missing stories and 20% for older backfill.

    Input is ordered newest-first. A story is never selected twice.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if len(set(missing)) != len(missing):
        raise ValueError("missing story IDs must be unique")
    if len(missing) <= limit:
        return list(missing)
    live = max(1, int(limit * 0.8))
    selected = missing[:live]
    backfill = list(reversed(missing))[: limit - live]
    return selected + backfill


def choose_audit_candidates(
    story_ids: list[UUID], *, newest_count: int, rotating_count: int,
    slot: int,
) -> list[UUID]:
    """Audit a bounded recent cohort and rotating older cohort per 15-min slot.

    Avoid repeatedly loading full coverage snapshots for every eligible story.
    A prime stride rotates the older cohort without a persisted cursor or
    extra database writes. Expensive currentness checks stay unchanged.
    """
    if newest_count < 0 or rotating_count < 0 or slot < 0:
        raise ValueError("audit limits and slot must not be negative")
    if len(set(story_ids)) != len(story_ids):
        raise ValueError("eligible story IDs must be unique")
    newest = story_ids[:newest_count]
    older = story_ids[len(newest):]
    if not older or not rotating_count:
        return newest
    start = (slot * 997) % len(older)
    return newest + [
        older[(start + index) % len(older)]
        for index in range(min(rotating_count, len(older)))
    ]


class TargetedMixin:
    pipeline: str

    def __init__(self, *args, target_ids: list[UUID], **kwargs):
        self.target_ids = target_ids
        self.cursor = 0
        super().__init__(*args, **kwargs)

    def _claim_pending(self, db, *, limit, now):
        claims = []
        # Avoid scanning/claiming the entire target list in one transaction.
        while self.cursor < len(self.target_ids) and len(claims) < limit:
            # Never advance past candidates the atomic claim gate was not
            # given room to process. Previously this selected limit*4
            # IDs, claimed at most limit, then permanently skipped the
            # remaining IDs in that chunk.
            capacity = limit - len(claims)
            chunk = self.target_ids[self.cursor:self.cursor + capacity]
            self.cursor += len(chunk)
            candidates = []
            for story_id in chunk:
                snapshot = self.service.load_snapshot(db, story_id=story_id)
                if snapshot is not None:
                    candidates.append(self.service.candidate(snapshot))
            if candidates:
                claims.extend(
                    self.processing_repository.claim_candidates(
                        db,
                        pipeline=self.pipeline,
                        candidates=candidates,
                        worker_id=self.worker_id,
                        now=now,
                        claim_expires_at=now + timedelta(
                            seconds=self.claim_ttl_seconds
                        ),
                        limit=limit - len(claims),
                    )
                )
        return claims


class TargetedClaimRelations(TargetedMixin, ClaimRelationRunner):
    pipeline = StoryPipeline.CLAIM_RELATIONS.value


class TargetedEvidence(TargetedMixin, EvidenceRunner):
    pipeline = StoryPipeline.EVIDENCE_ANALYSIS.value


class TargetedConsensus(TargetedMixin, ConsensusRunner):
    pipeline = StoryPipeline.CONSENSUS_ANALYSIS.value


class TargetedCoverage(TargetedMixin, CoverageRunner):
    pipeline = StoryPipeline.COVERAGE_ANALYSIS.value


def build_services():
    consensus = ConsensusService(
        analyzer=RuleBasedConsensusAnalyzer(
            minimum_independent_sources=settings.consensus_minimum_independent_sources
        )
    )
    coverage = CoverageService(
        analyzer=RuleBasedCoverageAnalyzer(
            minimum_independent_content_sources=(
                settings.coverage_minimum_independent_content_sources
            ),
        ),
        consensus_service=consensus,
    )
    relations = ClaimRelationService(
        analyzer=RuleBasedClaimRelationAnalyzer(
            group_similarity_threshold=settings.claim_relation_group_similarity_threshold,
            contradiction_similarity_threshold=(
                settings.claim_relation_contradiction_similarity_threshold
            ),
        )
    )
    evidence = EvidenceService(analyzer=RuleBasedEvidenceAnalyzer())
    return relations, evidence, consensus, coverage


def find_missing(
    coverage_service: CoverageService, *, target_limit: int,
    audit_deadline: float,
) -> tuple[int, list[UUID], int, int]:
    """Bound exact freshness checks so the scheduled job can process work.

    The earlier job read and verified *all* ~5,500 eligible StoryAnalysis
    snapshots at every invocation. Auditing alone took the entire 20-minute
    budget, leaving claim_relations cursor=0 on every run.
    """
    with SessionLocal() as db:
        story_ids = list(
            db.scalars(
                text("""
                    SELECT sa.story_id FROM story_articles sa
                    JOIN stories st ON st.id=sa.story_id AND st.deleted_at IS NULL
                    JOIN articles a ON a.id=sa.article_id AND a.deleted_at IS NULL
                    JOIN feeds f ON f.id=a.feed_id AND f.deleted_at IS NULL
                    WHERE sa.deleted_at IS NULL
                    GROUP BY sa.story_id
                    HAVING count(DISTINCT f.source_id)>=2
                       AND max(sa.article_time)<now()-interval '2 hours'
                    ORDER BY max(sa.article_time) DESC, sa.story_id
                """)
            ).all()
        )
        db.rollback()

    # Newer Stories receive repeated attention. For older Stories, the
    # rotating quarter-hour cohort prevents repeatedly inspecting the
    # same initial pages. It eventually samples the whole eligible set
    # without weakening the exact generation/hash checks.
    slot = int(datetime.now(UTC).timestamp() // 900)
    audit_ids = choose_audit_candidates(
        story_ids,
        newest_count=max(16, target_limit * 2),
        rotating_count=max(24, target_limit * 4),
        slot=slot,
    )
    analysis = StoryAnalysisService(coverage_service)
    missing: list[UUID] = []
    exceptions = checked = 0
    with SessionLocal() as db:
        for story_id in audit_ids:
            if monotonic() >= audit_deadline:
                break
            checked += 1
            try:
                if analysis.load(db, story_id=story_id) is None:
                    missing.append(story_id)
            except Exception:
                exceptions += 1
                missing.append(story_id)
                logging.exception("Integrated freshness audit failed for %s", story_id)
            finally:
                db.rollback()
    return len(story_ids), missing, exceptions, checked


def execute_stages(target_ids: list[UUID], deadline: float, batch_size: int) -> int:
    """Finish all four dependent generations for each Story before moving on.

    Running Claim Relations for *all* targets first starved Evidence,
    Consensus, and Coverage when the time budget expired. This resulted
    in no fully current public StoryAnalysis despite expensive work.
    One complete Story per pass is more useful than many partial Stories.
    The atomic processing claim gate and input-hash validation remain intact.
    """
    relations, evidence, consensus, coverage = build_services()
    configs = [
        ("claim_relations", TargetedClaimRelations, relations),
        ("evidence", TargetedEvidence, evidence),
        ("consensus", TargetedConsensus, consensus),
        ("coverage", TargetedCoverage, coverage),
    ]
    attempted_stories = 0
    any_progress = False
    for story_id in target_ids:
        for name, runner_type, service in configs:
            if monotonic() >= deadline:
                print(
                    f"TIME_BUDGET_EXHAUSTED stage={name} "
                    f"attempted_stories={attempted_stories} of {len(target_ids)}",
                    flush=True,
                )
                return 0 if any_progress else 1
            runner = runner_type(
                SessionLocal,
                service,
                target_ids=[story_id],
                claim_ttl_seconds=900,
            )
            result = runner.run_pending(limit=1)
            any_progress = any_progress or bool(result.processed)
            if result.failed:
                print(
                    f"STAGE_FAILURE stage={name} story_id={story_id} "
                    f"failed={result.failed}",
                    flush=True,
                )
                return 1
            print(
                f"STAGE_OK stage={name} story_id={story_id} "
                f"selected={result.selected} processed={result.processed} "
                f"skipped={result.skipped}",
                flush=True,
            )
        attempted_stories += 1
        # 'run_pending' may legitimately skip an in-flight/leased candidate.
        # Do not claim a StoryAnalysis is ready until the reader verifies it.
        print(
            f"STORY_STAGES_ATTEMPTED story_id={story_id} "
            f"attempted={attempted_stories} of {len(target_ids)}",
            flush=True,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-targets", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--max-minutes", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if min(args.max_targets, args.batch_size, args.max_minutes) < 1:
        parser.error("limits must be positive")

    logging.basicConfig(level=logging.WARNING)
    # Yield CPU to the nine required live workers on the 2-vCPU host.
    if os.name == "posix":
        os.nice(10)
    start = monotonic()
    _, _, _, coverage = build_services()
    deadline = start + args.max_minutes * 60
    audit_deadline = min(deadline, start + min(90, args.max_minutes * 12))
    eligible, missing, exceptions, checked = find_missing(
        coverage, target_limit=args.max_targets, audit_deadline=audit_deadline,
    )
    target_ids = choose_targets(missing, args.max_targets)
    print(
        f"AUDIT eligible={eligible} audited={checked} "
        f"current_in_sample={checked-len(missing)} "
        f"missing_in_sample={len(missing)} errors={exceptions} "
        f"targets={len(target_ids)}",
        flush=True,
    )
    if exceptions or (eligible and not checked):
        return 1
    if args.dry_run or not target_ids:
        return 0
    return execute_stages(
        target_ids,
        deadline=deadline,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    raise SystemExit(main())
