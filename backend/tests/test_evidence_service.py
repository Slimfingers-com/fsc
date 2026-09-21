from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.enums.story_pipeline import StoryPipeline
from app.evidence.provider import (
    ClaimEvidenceLinkResult,
    EvidenceItemResult,
    EvidenceKind,
    EvidenceRelationKind,
    StoryEvidenceAnalysisResult,
)
from app.models.evidence import StoryClaimEvidence, StoryEvidence
from app.models.story_processing import StoryProcessingRun
from app.services.evidence import EvidenceService
from tests.evidence_helpers import build_evidence_story


def add_active_evidence_run(db, service, prepared):
    run = StoryProcessingRun(
        story_id=prepared.story_id,
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
    return run


def test_service_persists_complete_evidence_generation(db):
    data = build_evidence_story(db)
    service = EvidenceService()

    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    result = service.run_provider(prepared)
    run = add_active_evidence_run(
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
        .select_from(StoryEvidence)
        .where(
            StoryEvidence.story_id == data["story"].id,
            StoryEvidence.deleted_at.is_(None),
        )
    ) == 2
    assert db.scalar(
        select(func.count())
        .select_from(StoryClaimEvidence)
        .where(
            StoryClaimEvidence.story_id == data["story"].id,
            StoryClaimEvidence.deleted_at.is_(None),
        )
    ) == 2


def test_processing_identity_tracks_claim_group_generation(db):
    data = build_evidence_story(db)
    service = EvidenceService()

    first = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert first is not None
    first_hash = service.analysis_hash(first)

    data["group"].group_hash = uuid4().hex * 2
    db.flush()

    second = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert second is not None
    assert service.analysis_hash(second) != first_hash


def test_invalid_provider_group_link_is_rejected(db):
    data = build_evidence_story(db)
    service = EvidenceService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    valid = service.run_provider(prepared)

    bad = StoryEvidenceAnalysisResult(
        evidence=valid.evidence,
        links=(
            ClaimEvidenceLinkResult(
                claim_group_id=uuid4(),
                evidence_key=valid.links[0].evidence_key,
                relation_kind=EvidenceRelationKind.SUPPORTS,
                confidence=1.0,
            ),
            *valid.links[1:],
        ),
    )

    with pytest.raises(
        ValueError,
        match="wrong claim group",
    ):
        service._validate_result(
            prepared=prepared,
            result=bad,
        )


def test_duplicate_claim_evidence_is_rejected(db):
    data = build_evidence_story(db)
    service = EvidenceService()
    snapshot = service.load_snapshot(
        db,
        story_id=data["story"].id,
    )
    assert snapshot is not None
    prepared = service.prepare(snapshot)
    claim = prepared.analysis_input.claims[0]

    result = StoryEvidenceAnalysisResult(
        evidence=(
            EvidenceItemResult(
                key="a",
                claim_id=claim.claim_id,
                evidence_kind=EvidenceKind.PRIMARY_SOURCE,
                evidence_text=claim.claim_text,
                confidence=1.0,
            ),
            EvidenceItemResult(
                key="b",
                claim_id=claim.claim_id,
                evidence_kind=EvidenceKind.PRIMARY_SOURCE,
                evidence_text=claim.claim_text,
                confidence=1.0,
            ),
        ),
        links=(),
    )

    with pytest.raises(
        ValueError,
        match="more than one evidence item",
    ):
        service._validate_result(
            prepared=prepared,
            result=result,
        )
