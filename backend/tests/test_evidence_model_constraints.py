from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums.story_pipeline import StoryPipeline
from app.evidence.provider import EvidenceKind, EvidenceRelationKind
from app.models.evidence import StoryClaimEvidence, StoryEvidence
from app.models.story_processing import StoryProcessingRun
from tests.evidence_helpers import build_evidence_story


def add_run(db, story):
    run = StoryProcessingRun(
        story_id=story.id,
        processing_state_id=None,
        pipeline=StoryPipeline.EVIDENCE_ANALYSIS.value,
        input_hash="e" * 64,
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


def make_evidence(data, run, *, confidence=0.9):
    return StoryEvidence(
        story_id=data["story"].id,
        processing_run_id=run.id,
        claim_id=data["claims"][0].id,
        article_id=data["articles"][0].id,
        source_id=data["sources"][0].id,
        evidence_kind=EvidenceKind.INDEPENDENT_REPORTING,
        evidence_text=data["claims"][0].claim_text,
        evidence_hash="a" * 64,
        confidence=confidence,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )


def test_evidence_confidence_constraint(db):
    data = build_evidence_story(db)
    run = add_run(db, data["story"])
    db.add(
        make_evidence(
            data,
            run,
            confidence=1.1,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_active_evidence_hash_per_story_claim_is_rejected(db):
    data = build_evidence_story(db)
    run = add_run(db, data["story"])
    first = make_evidence(data, run)
    db.add(first)
    db.flush()

    other_run = StoryProcessingRun(
        story_id=data["story"].id,
        processing_state_id=None,
        pipeline=StoryPipeline.EVIDENCE_ANALYSIS.value,
        input_hash="f" * 64,
        provider="test",
        provider_version="1",
        configuration_version="2",
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(other_run)
    db.flush()
    db.add(
        StoryEvidence(
            story_id=data["story"].id,
            processing_run_id=other_run.id,
            claim_id=data["claims"][0].id,
            article_id=data["articles"][0].id,
            source_id=data["sources"][0].id,
            evidence_kind=EvidenceKind.INDEPENDENT_REPORTING,
            evidence_text=data["claims"][0].claim_text,
            evidence_hash="a" * 64,
            confidence=0.9,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_claim_evidence_relation_constraint(db):
    data = build_evidence_story(db)
    run = add_run(db, data["story"])
    evidence = make_evidence(data, run)
    db.add(evidence)
    db.flush()

    db.add(
        StoryClaimEvidence(
            story_id=data["story"].id,
            processing_run_id=run.id,
            claim_group_id=data["group"].id,
            evidence_id=evidence.id,
            relation_kind="invalid",
            confidence=0.9,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
