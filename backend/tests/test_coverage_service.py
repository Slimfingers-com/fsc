from datetime import UTC, datetime

from sqlalchemy import func, select

from app.enums.coverage_scope import CoverageScope
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    SourceRelationKind,
)
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.coverage import (
    StoryCoverageGap,
    StoryCoverageSummary,
    StoryMissingPerspective,
)
from app.models.source_dependency import ArticleProvenance, SourceRelation
from app.models.story_processing import StoryProcessingRun
from app.services.coverage import CoverageService
from tests.consensus_helpers import build_consensus_story
from tests.coverage_helpers import (
    build_coverage_story,
    persist_current_consensus,
)


def add_run(
    db,
    service,
    prepared,
):
    run = StoryProcessingRun(
        story_id=prepared.story_id,
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .COVERAGE_ANALYSIS
            .value
        ),
        input_hash=(
            prepared.expected_hash
        ),
        provider=service.analyzer.provider,
        provider_version=(
            service.analyzer.version
        ),
        configuration_version=(
            service
            .processing_configuration_version
        ),
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    return run


def test_coverage_metrics_capture_source_distributions(db):
    data = build_coverage_story(
        db,
        specs=[
            {
                "source_type": SourceType.NEWS,
                "claim_text": "The plan begins Monday.",
                "ownership": "Owner A",
                "coverage_scope": CoverageScope.NATIONAL,
                "country": "DE",
            },
            {
                "source_type": SourceType.AGENCY,
                "claim_text": "The plan begins Monday.",
                "ownership": "Owner B",
                "coverage_scope": CoverageScope.INTERNATIONAL,
                "country": "US",
            },
        ],
    )
    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(
        snapshot
    )

    assert (
        prepared.metrics
        .independent_content_source_count
        == 2
    )
    assert (
        prepared.metrics.source_type_counts
        == {
            "NEWS": 1,
            "AGENCY": 1,
        }
    )
    assert (
        prepared.metrics
        .coverage_scope_counts
        == {
            "NATIONAL": 1,
            "INTERNATIONAL": 1,
        }
    )
    assert (
        prepared.metrics.country_counts
        == {
            "DE": 1,
            "US": 1,
        }
    )


def test_same_owner_does_not_reduce_independent_content_sources(db):
    data = build_coverage_story(
        db,
        same_owner=True,
    )
    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)

    assert prepared.metrics.independent_content_source_count == 2
    assert result.gaps == ()


def test_shared_newsroom_creates_observable_coverage_gap(db):
    data = build_coverage_story(
        db,
        shared_newsroom=True,
    )
    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)

    assert prepared.metrics.independent_content_source_count == 1
    assert len(result.gaps) == 1


def test_verified_supplier_provenance_creates_observable_coverage_gap(db):
    data = build_coverage_story(
        db,
        supplied_by_first=True,
    )
    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)

    assert prepared.metrics.independent_content_source_count == 1
    assert len(result.gaps) == 1


def test_stale_consensus_generation_is_rejected(db):
    data = build_coverage_story(db)
    service = CoverageService()

    assert (
        service.load_snapshot(
            db,
            story_id=data["story"].id,
        )
        is not None
    )

    db.add(
        SourceRelation(
            source_id=data["sources"][0].id,
            related_source_id=data["sources"][1].id,
            relation_kind=SourceRelationKind.SHARED_NEWSROOM,
        )
    )
    db.flush()

    assert (
        service.load_snapshot(
            db,
            story_id=data["story"].id,
        )
        is None
    )


def test_missing_perspective_keeps_contradiction_context(db):
    data = build_coverage_story(
        db,
        contradictory=True,
    )
    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(
        snapshot
    )
    result = service.run_provider(
        prepared
    )
    run = add_run(
        db,
        service,
        prepared,
    )
    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=result,
        processing_run_id=run.id,
        analyzed_at=datetime.now(UTC),
    )
    db.flush()

    missing = list(
        db.scalars(
            select(
                StoryMissingPerspective
            ).where(
                StoryMissingPerspective
                .story_id
                == data["story"].id,
                StoryMissingPerspective
                .deleted_at
                .is_(None),
            )
        ).all()
    )
    assert len(missing) == 2
    assert all(
        data["relation"].id
        in item.contradiction_relation_ids
        for item in missing
    )
    assert db.scalar(
        select(func.count())
        .select_from(
            StoryCoverageSummary
        )
        .where(
            StoryCoverageSummary
            .story_id
            == data["story"].id,
            StoryCoverageSummary
            .deleted_at
            .is_(None),
        )
    ) == 1


def test_co_production_bridges_coverage_independence_component(db):
    data = build_consensus_story(
        db,
        specs=[
            {
                "source_type": SourceType.NEWS,
                "claim_text": "The plan begins Monday.",
            },
            {
                "source_type": SourceType.NEWS,
                "claim_text": "The plan begins Monday.",
            },
            {
                "source_type": SourceType.NEWS,
                "claim_text": "The plan begins Monday.",
            },
        ],
    )

    data["articles"][2].feed.name = "Secondary"
    data["articles"][2].feed.source = data["sources"][1]
    db.add(
        ArticleProvenance(
            article_id=data["articles"][1].id,
            upstream_source_id=data["sources"][0].id,
            relation_kind=ArticleProvenanceKind.CO_PRODUCED_WITH,
            confidence=1.0,
            detection_method=ArticleProvenanceDetectionMethod.MANUAL,
            verified=True,
        )
    )
    db.flush()
    persist_current_consensus(db, data)

    service = CoverageService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None

    prepared = service.prepare(snapshot)

    assert prepared.metrics.independent_content_source_count == 1
    assert len({
        item.independence_key
        for item in prepared.analysis_input.sources
    }) == 1
