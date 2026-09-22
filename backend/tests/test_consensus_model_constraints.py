from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.consensus.provider import ConsensusKind, DifferenceKind
from app.enums.story_pipeline import StoryPipeline
from app.models.consensus import StoryConsensusSummary, StoryDifferenceSummary
from app.models.story_processing import StoryProcessingRun
from tests.consensus_helpers import build_consensus_story


def add_run(db, story):
    run = StoryProcessingRun(
        story_id=story.id,
        processing_state_id=None,
        pipeline=StoryPipeline.CONSENSUS_ANALYSIS.value,
        input_hash="c" * 64,
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(run)
    db.flush()
    return run


def test_consensus_count_constraint(db):
    data = build_consensus_story(db)
    run = add_run(db, data["story"])
    db.add(
        StoryConsensusSummary(
            story_id=data["story"].id,
            processing_run_id=run.id,
            claim_group_id=data["group"].id,
            consensus_kind=ConsensusKind.SHARED,
            claim_count=2,
            article_count=2,
            independent_source_count=0,
            evidence_item_count=2,
            evidence_source_count=2,
            attributed_perspective_count=0,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_difference_requires_distinct_groups(db):
    data = build_consensus_story(
        db,
        contradictory=True,
    )
    run = add_run(db, data["story"])
    db.add(
        StoryDifferenceSummary(
            story_id=data["story"].id,
            processing_run_id=run.id,
            claim_relation_id=data["relation"].id,
            left_group_id=data["group"].id,
            right_group_id=data["group"].id,
            difference_kind=DifferenceKind.CONTRADICTION,
            left_independent_source_count=1,
            right_independent_source_count=1,
            left_evidence_source_count=1,
            right_evidence_source_count=1,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
