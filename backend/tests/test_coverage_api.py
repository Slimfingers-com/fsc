from datetime import UTC, datetime

from app.enums.story_pipeline import StoryPipeline
from app.models.story_processing import StoryProcessingRun
from app.services.coverage import CoverageService
from tests.coverage_helpers import build_coverage_story


def persist_coverage(db, data):
    service = CoverageService()
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
        pipeline=StoryPipeline.COVERAGE_ANALYSIS.value,
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
    return run


def test_coverage_endpoints(client, db):
    data = build_coverage_story(
        db,
        shared_newsroom=True,
    )
    persist_coverage(db, data)

    summary = client.get(
        f"/stories/{data['story'].id}/coverage"
    )
    assert summary.status_code == 200
    assert (
        summary.json()[
            "independent_content_source_count"
        ]
        == 1
    )

    gaps = client.get(
        f"/stories/{data['story'].id}/coverage-gaps"
    )
    assert gaps.status_code == 200
    assert gaps.json()["total"] == 1
    assert (
        gaps.json()["items"][0]["gap_kind"]
        == "limited_independent_content_sources"
    )

    missing = client.get(
        f"/stories/{data['story'].id}/missing-perspectives"
    )
    assert missing.status_code == 200
    assert missing.json()["total"] == 1


def test_coverage_reads_hide_stale_consensus_generation(client, db):
    data = build_coverage_story(db)
    persist_coverage(db, data)

    old_run = data["consensus_run"]
    old_run.finished_at = old_run.finished_at
    new_run = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=StoryPipeline.CONSENSUS_ANALYSIS.value,
        input_hash="b" * 64,
        provider="local-rules",
        provider_version="1.0.0",
        configuration_version="different",
        worker_id="test",
        attempt_number=2,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(new_run)
    db.flush()

    # Simulate activation of a newer consensus generation.
    from app.models.consensus import StoryConsensusSummary
    existing = db.query(StoryConsensusSummary).filter(
        StoryConsensusSummary.story_id == data["story"].id,
        StoryConsensusSummary.deleted_at.is_(None),
    ).all()
    for item in existing:
        item.processing_run_id = new_run.id
    db.flush()

    assert client.get(
        f"/stories/{data['story'].id}/coverage"
    ).status_code == 404
    assert client.get(
        f"/stories/{data['story'].id}/coverage-gaps"
    ).json()["total"] == 0
    assert client.get(
        f"/stories/{data['story'].id}/missing-perspectives"
    ).json()["total"] == 0


def test_missing_perspective_hidden_when_group_member_ineligible(client, db):
    data = build_coverage_story(db)
    persist_coverage(db, data)

    data["sources"][0].active = False
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/missing-perspectives"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
