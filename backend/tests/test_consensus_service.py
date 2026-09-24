from datetime import UTC, datetime

from sqlalchemy import func, select

from app.consensus.provider import ConsensusKind, DifferenceKind
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
)
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.consensus import (
    StoryConsensusSummary,
    StoryDifferenceSummary,
)
from app.models.source_dependency import ArticleProvenance
from app.models.story_processing import StoryProcessingRun
from app.services.consensus import ConsensusService
from tests.consensus_helpers import build_consensus_story


def add_run(db, service, prepared):
    run = StoryProcessingRun(
        story_id=prepared.story_id,
        processing_state_id=None,
        pipeline=StoryPipeline.CONSENSUS_ANALYSIS.value,
        input_hash=prepared.expected_hash,
        provider=service.analyzer.provider,
        provider_version=service.analyzer.version,
        configuration_version=service.processing_configuration_version,
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    return run


def test_distinct_owners_count_as_independent_sources(db):
    data = build_consensus_story(
        db,
        same_owner=False,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)

    assert len(prepared.analysis_input.groups) == 1
    group = prepared.analysis_input.groups[0]
    assert group.independent_source_count == 2
    assert group.article_count == 2

    result = service.run_provider(prepared)
    assert result.consensus[0].consensus_kind == ConsensusKind.SHARED


def test_same_owner_sources_still_count_as_independent(db):
    data = build_consensus_story(
        db,
        same_owner=True,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)

    group = prepared.analysis_input.groups[0]
    assert group.article_count == 2
    assert group.independent_source_count == 2

    result = service.run_provider(prepared)
    assert result.consensus[0].consensus_kind == ConsensusKind.SHARED


def test_shared_newsroom_sources_count_as_one_independent_source(db):
    data = build_consensus_story(
        db,
        shared_newsroom=True,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)

    group = prepared.analysis_input.groups[0]
    assert group.independent_source_count == 1
    result = service.run_provider(prepared)
    assert (
        result.consensus[0].consensus_kind
        == ConsensusKind.SINGLE_SOURCE
    )


def test_verified_supplier_provenance_counts_as_one_independent_source(db):
    data = build_consensus_story(
        db,
        supplied_by_first=True,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)

    assert prepared.analysis_input.groups[0].independent_source_count == 1


def test_unverified_supplier_provenance_does_not_reduce_independence(db):
    data = build_consensus_story(
        db,
        supplied_by_first=True,
        verified_provenance=False,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)

    assert prepared.analysis_input.groups[0].independent_source_count == 2


def test_contradiction_creates_difference_summary(db):
    data = build_consensus_story(
        db,
        contradictory=True,
    )
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)

    assert len(result.consensus) == 2
    assert len(result.differences) == 1
    assert (
        result.differences[0].difference_kind
        == DifferenceKind.CONTRADICTION
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

    assert db.scalar(
        select(func.count())
        .select_from(StoryConsensusSummary)
        .where(
            StoryConsensusSummary.story_id == data["story"].id,
            StoryConsensusSummary.deleted_at.is_(None),
        )
    ) == 2
    assert db.scalar(
        select(func.count())
        .select_from(StoryDifferenceSummary)
        .where(
            StoryDifferenceSummary.story_id == data["story"].id,
            StoryDifferenceSummary.deleted_at.is_(None),
        )
    ) == 1


def test_co_production_bridges_story_independence_component(db):
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

    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None

    prepared = service.prepare(snapshot)

    assert len(prepared.analysis_input.groups) == 1
    assert prepared.analysis_input.groups[0].article_count == 3
    assert prepared.analysis_input.groups[0].independent_source_count == 1
