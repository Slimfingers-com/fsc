from datetime import UTC, datetime

from app.enums.story_pipeline import StoryPipeline
from app.models.claim_relation import StoryClaimGroupMember
from app.models.evidence import StoryEvidence
from app.models.source import Source
from app.models.story_processing import StoryProcessingRun
from tests.conftest import TestSessionLocal
from tests.coverage_helpers import (
    build_complete_analysis_story,
    build_coverage_story,
)


def test_story_analysis_composes_all_current_generations(
    client,
    db,
):
    data = build_complete_analysis_story(
        db,
        contradictory=True,
    )

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["story_id"] == str(
        data["story"].id
    )
    assert (
        payload["generations"][
            "claim_relations_run_id"
        ]
        == str(data["relation_run"].id)
    )
    assert (
        payload["generations"][
            "evidence_run_id"
        ]
        == str(data["evidence_run"].id)
    )
    assert (
        payload["generations"][
            "consensus_run_id"
        ]
        == str(data["consensus_run"].id)
    )
    assert (
        payload["generations"][
            "coverage_run_id"
        ]
        == str(data["coverage_run"].id)
    )

    assert len(
        payload["claim_groups"]
    ) == 2
    assert sum(
        len(group["evidence"])
        for group in payload["claim_groups"]
    ) == 2
    assert len(
        payload["differences"]
    ) == 1
    assert (
        payload["differences"][0][
            "difference_kind"
        ]
        == "contradiction"
    )
    assert (
        payload["coverage"][
            "claim_group_count"
        ]
        == 2
    )
    assert all(
        group["missing_perspective"]
        is not None
        for group
        in payload["claim_groups"]
    )

    assert "truth_score" not in payload
    assert "credibility_score" not in payload


def test_story_analysis_is_unavailable_before_coverage(
    client,
    db,
):
    data = build_coverage_story(db)

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Current story analysis "
        "is not available."
    )


def test_story_analysis_hides_stale_coverage_after_metadata_change(
    client,
    db,
):
    data = build_complete_analysis_story(
        db
    )

    assert client.get(
        f"/stories/{data['story'].id}/analysis"
    ).status_code == 200

    data["sources"][0].country = "DE"
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )

    assert response.status_code == 404


def test_story_analysis_rejects_mixed_evidence_generation(
    client,
    db,
):
    data = build_complete_analysis_story(
        db
    )

    replacement = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .EVIDENCE_ANALYSIS
            .value
        ),
        input_hash="e" * 64,
        provider="local-rules",
        provider_version="1.0.0",
        configuration_version="mixed",
        worker_id="test",
        attempt_number=2,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(replacement)
    db.flush()

    evidence = (
        db.query(StoryEvidence)
        .filter(
            StoryEvidence.story_id
            == data["story"].id,
            StoryEvidence.deleted_at.is_(None),
        )
        .first()
    )
    assert evidence is not None
    evidence.processing_run_id = (
        replacement.id
    )
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )

    assert response.status_code == 404


def test_missing_story_returns_404(
    client,
):
    from uuid import uuid4

    response = client.get(
        f"/stories/{uuid4()}/analysis"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Story not found."
    )



def test_story_analysis_rejects_change_during_composition(
    client,
    db,
    monkeypatch,
):
    data = build_complete_analysis_story(
        db
    )

    from app.api.story_analysis import service

    original = (
        service.coverage_service
        .load_snapshot
    )
    calls = 0

    def changing_snapshot(
        session,
        *,
        story_id,
        **kwargs,
    ):
        nonlocal calls
        calls += 1
        if calls == 2:
            data["sources"][0].country = (
                "DE"
            )
            session.flush()
        return original(
            session,
            story_id=story_id,
            **kwargs,
        )

    monkeypatch.setattr(
        service.coverage_service,
        "load_snapshot",
        changing_snapshot,
    )

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )

    assert calls >= 2
    assert response.status_code == 404



def test_story_analysis_rejects_external_commit_during_composition(
    monkeypatch,
):
    with TestSessionLocal.begin() as setup_db:
        data = build_complete_analysis_story(
            setup_db
        )
        story_id = data["story"].id
        source_id = data["sources"][0].id

    from app.api.story_analysis import service

    original = (
        service.coverage_service
        .load_snapshot
    )
    calls = 0

    def changing_snapshot(
        session,
        *,
        story_id,
        **kwargs,
    ):
        nonlocal calls
        calls += 1
        if calls == 2:
            with TestSessionLocal.begin() as external_db:
                source = external_db.get(
                    Source,
                    source_id,
                )
                assert source is not None
                source.country = "DE"
        return original(
            session,
            story_id=story_id,
            **kwargs,
        )

    monkeypatch.setattr(
        service.coverage_service,
        "load_snapshot",
        changing_snapshot,
    )

    with TestSessionLocal() as request_db:
        result = service.load(
            request_db,
            story_id=story_id,
        )

    assert calls >= 2
    assert result is None


def test_story_analysis_rejects_mixed_claim_group_member_generation(
    client,
    db,
):
    data = build_complete_analysis_story(
        db
    )

    replacement = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .CLAIM_RELATIONS
            .value
        ),
        input_hash="r" * 64,
        provider="test",
        provider_version="1",
        configuration_version="mixed",
        worker_id="test",
        attempt_number=2,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(replacement)
    db.flush()

    member = (
        db.query(
            StoryClaimGroupMember
        )
        .filter(
            StoryClaimGroupMember.deleted_at
            .is_(None)
        )
        .first()
    )
    assert member is not None
    member.processing_run_id = (
        replacement.id
    )
    db.flush()

    response = client.get(
        f"/stories/{data['story'].id}/analysis"
    )

    assert response.status_code == 404
