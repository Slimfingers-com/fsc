from datetime import UTC, datetime

from sqlalchemy import func, select

from app.evidence.rule_based import RuleBasedEvidenceAnalyzer
from app.models.claim_relation import StoryClaimGroup
from app.models.evidence import StoryEvidence
from app.models.story_processing import StoryProcessingState
from app.enums.story_pipeline import StoryPipeline
from app.services.evidence import EvidenceRunner, EvidenceService
from tests.conftest import TestSessionLocal
from tests.evidence_helpers import build_evidence_story


def create_committed_story():
    with TestSessionLocal.begin() as db:
        data = build_evidence_story(db)
        return (
            data["story"].id,
            data["group"].id,
        )


def make_runner(
    worker_id: str,
    analyzer=None,
):
    return EvidenceRunner(
        TestSessionLocal,
        EvidenceService(
            analyzer=(
                analyzer
                or RuleBasedEvidenceAnalyzer()
            )
        ),
        worker_id=worker_id,
    )


class MutatingEvidenceAnalyzer(
    RuleBasedEvidenceAnalyzer
):
    provider = "mutating-evidence-test"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.mutated = False

    def analyze(self, story):
        result = super().analyze(story)
        if not self.mutated and story.claims:
            group_id = story.claims[0].claim_group_id
            with TestSessionLocal.begin() as db:
                group = db.get(
                    StoryClaimGroup,
                    group_id,
                )
                assert group is not None
                group.confidence = 0.77
            self.mutated = True
        return result


def test_runner_processes_once_and_reprocesses_changed_group():
    story_id, group_id = create_committed_story()
    runner = make_runner("evidence-worker")

    first = runner.run_pending(limit=1)
    assert first.processed == 1

    second = runner.run_pending(limit=1)
    assert second.selected == 0

    with TestSessionLocal.begin() as db:
        group = db.get(
            StoryClaimGroup,
            group_id,
        )
        assert group is not None
        group.confidence = 0.82

    third = runner.run_pending(limit=1)
    assert third.processed == 1

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(StoryEvidence)
            .where(
                StoryEvidence.story_id == story_id,
            )
        ) == 4

        assert db.scalar(
            select(func.count())
            .select_from(StoryEvidence)
            .where(
                StoryEvidence.story_id == story_id,
                StoryEvidence.deleted_at.is_(None),
            )
        ) == 2

        state = db.scalar(
            select(StoryProcessingState).where(
                StoryProcessingState.story_id == story_id,
                StoryProcessingState.pipeline
                == StoryPipeline.EVIDENCE_ANALYSIS.value,
            )
        )
        assert state is not None
        assert state.attempt_count == 2


def test_runner_discards_stale_provider_result():
    story_id, _ = create_committed_story()
    runner = make_runner(
        "stale-evidence-worker",
        analyzer=MutatingEvidenceAnalyzer(),
    )

    first = runner.run_pending(limit=1)

    assert (
        first.selected,
        first.processed,
        first.skipped,
        first.failed,
    ) == (
        1,
        0,
        1,
        0,
    )

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(StoryEvidence)
            .where(
                StoryEvidence.story_id == story_id,
                StoryEvidence.deleted_at.is_(None),
            )
        ) == 0

    second = runner.run_pending(limit=1)
    assert second.processed == 1
