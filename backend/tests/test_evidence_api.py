from datetime import UTC, datetime

from app.enums.story_pipeline import StoryPipeline
from app.models.story_processing import StoryProcessingRun
from app.services.evidence import EvidenceService
from tests.evidence_helpers import build_evidence_story


def persist_evidence(db, data):
    service = EvidenceService()
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
        pipeline=StoryPipeline.EVIDENCE_ANALYSIS.value,
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


def test_story_and_group_evidence_endpoints(client, db):
    data = build_evidence_story(db)
    persist_evidence(db, data)

    story_response = client.get(
        f"/stories/{data['story'].id}/evidence"
    )
    assert story_response.status_code == 200
    payload = story_response.json()
    assert payload["total"] == 2
    assert {
        item["relation_kind"]
        for item in payload["items"]
    } == {"supports"}

    group_response = client.get(
        f"/claim-groups/{data['group'].id}/evidence",
        params={
            "evidence_kind": "primary_source",
        },
    )
    assert group_response.status_code == 200
    assert group_response.json()["total"] == 1


def test_evidence_reads_hide_group_with_ineligible_representative(client, db):
    data = build_evidence_story(db)
    persist_evidence(db, data)

    data["sources"][0].active = False
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/evidence"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_missing_story_and_group_return_404(client):
    from uuid import uuid4

    missing = uuid4()
    assert client.get(
        f"/stories/{missing}/evidence"
    ).status_code == 404
    assert client.get(
        f"/claim-groups/{missing}/evidence"
    ).status_code == 404
