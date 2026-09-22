from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.coverage.provider import (
    CoverageGapKind,
    MissingPerspectiveKind,
)
from app.enums.story_pipeline import StoryPipeline
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.story_processing import StoryProcessingRun
from tests.coverage_helpers import build_coverage_story


def add_run(db, data):
    run = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=StoryPipeline.COVERAGE_ANALYSIS.value,
        input_hash="a" * 64,
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


def test_coverage_summary_rejects_negative_counts(db):
    data = build_coverage_story(db)
    run = add_run(db, data)
    db.add(
        StoryCoverageSummary(
            story_id=data["story"].id,
            processing_run_id=run.id,
            consensus_processing_run_id=data["consensus_run"].id,
            article_count=2,
            source_count=2,
            content_source_count=2,
            signal_source_count=0,
            independent_content_owner_count=-1,
            claim_group_count=1,
            shared_group_count=1,
            difference_count=0,
            attributed_group_count=0,
            source_type_counts={},
            coverage_scope_counts={},
            country_counts={},
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_coverage_gap_rejects_negative_observed_count(db):
    data = build_coverage_story(db)
    run = add_run(db, data)
    db.add(
        StoryCoverageGap(
            story_id=data["story"].id,
            processing_run_id=run.id,
            gap_key="bad",
            gap_kind=(
                CoverageGapKind
                .LIMITED_INDEPENDENT_CONTENT_SOURCES
            ),
            observed_count=-1,
            minimum_expected=2,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_missing_perspective_kind_constraint(db):
    data = build_coverage_story(db)
    run = add_run(db, data)
    db.add(
        StoryMissingPerspective(
            story_id=data["story"].id,
            processing_run_id=run.id,
            claim_group_id=data["group"].id,
            missing_kind="invalid",
            contradiction_relation_ids=[],
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
