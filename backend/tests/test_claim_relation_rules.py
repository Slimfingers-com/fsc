from uuid import uuid4

from app.claim_relations.provider import (
    ClaimRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimInput,
)
from app.claim_relations.rule_based import (
    RuleBasedClaimRelationAnalyzer,
)


def make_claim(
    text: str,
    *,
    article_id=None,
    source_id=None,
):
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=(
            article_id
            or uuid4()
        ),
        source_id=(
            source_id
            or uuid4()
        ),
        claim_text=text,
        normalized_claim=(
            text.casefold().rstrip(".")
        ),
        claim_hash=(
            uuid4().hex * 2
        ),
        confidence=0.9,
    )


def analyze(*claims):
    return (
        RuleBasedClaimRelationAnalyzer()
        .analyze(
            StoryClaimAnalysisInput(
                story_id=uuid4(),
                language_code="en",
                claims=tuple(claims),
            )
        )
    )


def test_exact_and_close_claims_share_group():
    first = make_claim(
        "The climate plan begins on Monday."
    )
    second = make_claim(
        "The climate plan begins Monday."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 1
    assert {
        member.claim_id
        for member
        in result.groups[0].members
    } == {
        first.claim_id,
        second.claim_id,
    }


def test_opposite_negation_creates_contradiction():
    first = make_claim(
        "The climate plan will begin Monday."
    )
    second = make_claim(
        "The climate plan will not begin Monday."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 2
    assert len(result.relations) == 1
    assert (
        result.relations[0].relation_kind
        == ClaimRelationKind.CONTRADICTS
    )


def test_different_numbers_do_not_merge_or_contradict():
    first = make_claim(
        "The package costs 5 billion euros."
    )
    second = make_claim(
        "The package costs 50 billion euros."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 2
    assert result.relations == ()


def test_low_overlap_claims_remain_separate():
    result = analyze(
        make_claim(
            "The parliament approved the climate package."
        ),
        make_claim(
            "Flood warnings remain in force across the region."
        ),
    )

    assert len(result.groups) == 2


def test_role_reversal_does_not_share_group():
    first = make_claim(
        "Alice attacked Bob."
    )
    second = make_claim(
        "Bob attacked Alice."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 2


def test_role_reversal_with_negation_does_not_create_contradiction():
    first = make_claim(
        "Alice never attacked Bob."
    )
    second = make_claim(
        "Bob attacked Alice."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 2
    assert result.relations == ()


def test_german_negation_creates_contradiction_for_same_ordered_claim():
    first = make_claim(
        "Der Plan beginnt am Montag."
    )
    second = make_claim(
        "Der Plan beginnt nicht am Montag."
    )

    result = analyze(
        first,
        second,
    )

    assert len(result.groups) == 2
    assert len(result.relations) == 1
    assert (
        result.relations[0].relation_kind
        == ClaimRelationKind.CONTRADICTS
    )
