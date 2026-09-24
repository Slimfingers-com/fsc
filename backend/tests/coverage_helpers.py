from datetime import UTC, datetime

from app.enums.story_pipeline import StoryPipeline
from app.models.story_processing import StoryProcessingRun
from app.services.consensus import ConsensusService
from tests.consensus_helpers import build_consensus_story


def persist_current_consensus(
    db,
    data,
):
    service = ConsensusService()
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

    run = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .CONSENSUS_ANALYSIS
            .value
        ),
        input_hash=prepared.expected_hash,
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
    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=result,
        processing_run_id=run.id,
        analyzed_at=datetime.now(UTC),
    )
    run.finished_at = datetime.now(UTC)
    run.outcome = "succeeded"
    db.flush()
    data["consensus_run"] = run
    return run


def build_coverage_story(
    db,
    *,
    same_owner: bool = False,
    contradictory: bool = False,
    shared_newsroom: bool = False,
    supplied_by_first: bool = False,
    verified_provenance: bool = True,
    specs=None,
):
    data = build_consensus_story(
        db,
        same_owner=same_owner,
        contradictory=contradictory,
        shared_newsroom=shared_newsroom,
        supplied_by_first=supplied_by_first,
        verified_provenance=verified_provenance,
        specs=specs,
    )
    persist_current_consensus(
        db,
        data,
    )
    return data



def persist_current_coverage(
    db,
    data,
):
    from app.services.coverage import CoverageService

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
    run = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .COVERAGE_ANALYSIS
            .value
        ),
        input_hash=prepared.expected_hash,
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
    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=result,
        processing_run_id=run.id,
        analyzed_at=datetime.now(UTC),
    )
    run.finished_at = datetime.now(UTC)
    run.outcome = "succeeded"
    db.flush()
    data["coverage_run"] = run
    return run


def build_complete_analysis_story(
    db,
    *,
    same_owner: bool = False,
    contradictory: bool = False,
    specs=None,
):
    data = build_coverage_story(
        db,
        same_owner=same_owner,
        contradictory=contradictory,
        specs=specs,
    )
    persist_current_coverage(
        db,
        data,
    )
    return data
