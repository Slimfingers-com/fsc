from datetime import UTC, datetime

from app.enums.story_pipeline import StoryPipeline
from app.models.story_processing import StoryProcessingRun
from app.services.consensus import ConsensusService
from tests.consensus_helpers import build_consensus_story


def persist_consensus(db, data):
    service = ConsensusService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)
    run = StoryProcessingRun(
        story_id=data["story"].id,
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
    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=result,
        processing_run_id=run.id,
        analyzed_at=datetime.now(UTC),
    )
    db.flush()


def test_consensus_endpoint_exposes_shared_group(client, db):
    data = build_consensus_story(
        db,
        same_owner=False,
    )
    persist_consensus(db, data)

    response = client.get(
        f"/stories/{data['story'].id}/consensus"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["consensus_kind"] == "shared"
    assert payload["items"][0]["independent_source_count"] == 2


def test_differences_endpoint_exposes_contradiction(client, db):
    data = build_consensus_story(
        db,
        contradictory=True,
    )
    persist_consensus(db, data)

    response = client.get(
        f"/stories/{data['story'].id}/differences"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["difference_kind"] == "contradiction"


def test_consensus_read_hides_ineligible_representative(client, db):
    data = build_consensus_story(db)
    persist_consensus(db, data)

    data["sources"][0].active = False
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/consensus"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
