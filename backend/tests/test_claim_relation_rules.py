from uuid import uuid4

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
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


def make_semantic_claim(
    text: str,
    vector: tuple[float, ...] = (1.0, 0.0, 0.0),
):
    claim = make_claim(text)
    return StoryClaimInput(
        claim_id=claim.claim_id,
        article_id=claim.article_id,
        source_id=claim.source_id,
        claim_text=claim.claim_text,
        normalized_claim=claim.normalized_claim,
        claim_hash=claim.claim_hash,
        confidence=claim.confidence,
        semantic_embedding=vector,
        semantic_model="test-embedding",
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


def test_negation_in_additional_detail_is_not_hard_contradiction():
    first = make_claim(
        "Israel election committee excludes Arab parties."
    )
    second = make_claim(
        "Israel election committee excludes Arab parties, not far-right parties."
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


def test_semantic_grouping_recovers_same_language_paraphrase():
    first = make_semantic_claim(
        "Nordkorea feuert erneut ballistische Rakete ab."
    )
    second = make_semantic_claim(
        "Nordkorea hat erneut eine Rakete abgefeuert."
    )

    result = analyze(first, second)

    assert len(result.groups) == 1
    assert any(
        member.match_kind == ClaimGroupMatchKind.SEMANTIC
        for member in result.groups[0].members
    )


def test_semantic_grouping_requires_same_language_lexical_floor():
    first = make_semantic_claim(
        "The government approved the climate package."
    )
    second = make_semantic_claim(
        "Flood warnings remain in force across the region."
    )

    result = analyze(first, second)

    assert len(result.groups) == 2


def test_semantic_grouping_rejects_publishing_meta_claims():
    first = make_semantic_claim(
        "READ IN FULL: Trump and tech leaders' White House Accord."
    )
    second = make_semantic_claim(
        "Trump and tech leaders sign the White House Accord."
    )

    result = analyze(first, second)

    assert len(result.groups) == 2


def test_semantic_grouping_rejects_relative_time_mismatch():
    first = make_semantic_claim(
        "Selenskyj announced a meeting with Trump this week in New York."
    )
    second = make_semantic_claim(
        "Selenskyj plans talks with Trump in New York."
    )

    result = analyze(first, second)

    assert len(result.groups) == 2
