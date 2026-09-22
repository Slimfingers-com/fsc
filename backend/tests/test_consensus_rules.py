from uuid import uuid4

from app.consensus.provider import (
    ClaimDifferenceInput,
    ClaimGroupConsensusInput,
    ConsensusKind,
    DifferenceKind,
    StoryConsensusInput,
)
from app.consensus.rule_based import RuleBasedConsensusAnalyzer


def group(source_count: int):
    return ClaimGroupConsensusInput(
        group_id=uuid4(),
        representative_claim_id=uuid4(),
        representative_claim_text="The plan begins Monday.",
        claim_count=max(source_count, 1),
        article_count=max(source_count, 1),
        independent_source_count=source_count,
        evidence_item_count=max(source_count, 1),
        evidence_source_count=max(source_count, 1),
        attributed_perspective_count=0,
    )


def test_two_independent_sources_are_shared_consensus():
    item = group(2)
    result = RuleBasedConsensusAnalyzer().analyze(
        StoryConsensusInput(
            story_id=uuid4(),
            language_code="en",
            groups=(item,),
            differences=(),
        )
    )
    assert result.consensus[0].consensus_kind == ConsensusKind.SHARED


def test_one_independent_source_is_not_shared_consensus():
    item = group(1)
    result = RuleBasedConsensusAnalyzer().analyze(
        StoryConsensusInput(
            story_id=uuid4(),
            language_code="en",
            groups=(item,),
            differences=(),
        )
    )
    assert (
        result.consensus[0].consensus_kind
        == ConsensusKind.SINGLE_SOURCE
    )


def test_contradiction_is_reported_as_difference():
    left = group(1)
    right = group(1)
    relation_id = uuid4()
    result = RuleBasedConsensusAnalyzer().analyze(
        StoryConsensusInput(
            story_id=uuid4(),
            language_code="en",
            groups=(left, right),
            differences=(
                ClaimDifferenceInput(
                    relation_id=relation_id,
                    left_group_id=left.group_id,
                    right_group_id=right.group_id,
                    left_claim_text="The plan begins Monday.",
                    right_claim_text="The plan does not begin Monday.",
                    left_independent_source_count=1,
                    right_independent_source_count=1,
                    left_evidence_source_count=1,
                    right_evidence_source_count=1,
                ),
            ),
        )
    )
    assert len(result.differences) == 1
    assert result.differences[0].relation_id == relation_id
    assert (
        result.differences[0].difference_kind
        == DifferenceKind.CONTRADICTION
    )
