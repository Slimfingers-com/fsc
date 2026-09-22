from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.claim_relations.provider import ClaimRelationKind
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimGroupMember,
    StoryClaimRelation,
)
from app.models.story_processing import StoryProcessingRun
from app.services.evidence import EvidenceService
from tests.evidence_helpers import build_evidence_story


def persist_current_evidence(db, data):
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
    run.finished_at = datetime.now(UTC)
    run.outcome = "succeeded"
    db.flush()
    return run


def build_consensus_story(
    db,
    *,
    same_owner: bool = False,
    contradictory: bool = False,
    specs=None,
):
    ownership_a = "Shared Media Group" if same_owner else "Owner A"
    ownership_b = "Shared Media Group" if same_owner else "Owner B"
    data = build_evidence_story(
        db,
        specs=(
            specs
            or [
                {
                    "source_type": SourceType.NEWS,
                    "claim_text": "The plan begins Monday.",
                    "ownership": ownership_a,
                },
                {
                    "source_type": SourceType.AGENCY,
                    "claim_text": (
                        "The plan does not begin Monday."
                        if contradictory
                        else "The plan begins Monday."
                    ),
                    "ownership": ownership_b,
                },
            ]
        ),
    )

    if contradictory:
        first_claim, second_claim = data["claims"]
        first_group = data["group"]

        second_member = db.scalar(
            select(StoryClaimGroupMember).where(
                StoryClaimGroupMember.group_id == first_group.id,
                StoryClaimGroupMember.claim_id == second_claim.id,
            )
        )
        assert second_member is not None
        db.delete(second_member)
        db.flush()

        second_group = StoryClaimGroup(
            story_id=data["story"].id,
            processing_run_id=data["relation_run"].id,
            representative_claim_id=second_claim.id,
            group_hash=uuid4().hex * 2,
            confidence=0.9,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
        db.add(second_group)
        db.flush()
        db.add(
            StoryClaimGroupMember(
                group_id=second_group.id,
                claim_id=second_claim.id,
                processing_run_id=data["relation_run"].id,
                similarity_score=1.0,
                match_kind="exact",
            )
        )
        relation = StoryClaimRelation(
            story_id=data["story"].id,
            processing_run_id=data["relation_run"].id,
            left_group_id=first_group.id,
            right_group_id=second_group.id,
            relation_kind=ClaimRelationKind.CONTRADICTS,
            confidence=0.95,
            analysis_provider="test",
            analysis_version="1",
            analyzed_at=datetime.now(UTC),
        )
        db.add(relation)
        db.flush()
        data["second_group"] = second_group
        data["relation"] = relation

    data["evidence_run"] = persist_current_evidence(
        db,
        data,
    )
    return data
