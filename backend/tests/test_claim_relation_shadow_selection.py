from uuid import uuid4

from app.claim_relations.hybrid import HybridClaimRelationAnalyzer
from app.claim_relations.provider import (
    SemanticRelationCandidate,
    StoryClaimInput,
)
from scripts.evaluate_claim_relation_shadow import (
    candidate_batches,
    conflict_hint,
    rank_conflict_candidates,
)


def make_claim(text: str) -> StoryClaimInput:
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        normalized_claim=text.casefold(),
        claim_hash="test",
        confidence=1.0,
        article_title="Shared story",
        article_context=None,
    )


def make_candidate(
    left: str,
    right: str,
    *,
    score: float = 0.7,
) -> SemanticRelationCandidate:
    return SemanticRelationCandidate(
        story_id=uuid4(),
        language_code="en",
        left_group_key="left",
        right_group_key="right",
        left_claim=make_claim(left),
        right_claim=make_claim(right),
        candidate_score=score,
    )


def test_candidate_batches_preserves_all_candidates():
    candidates = tuple(
        make_candidate(
            f"left {index}",
            f"right {index}",
        )
        for index in range(10)
    )

    batches = candidate_batches(candidates, 4)

    assert tuple(map(len, batches)) == (4, 4, 2)
    assert tuple(item for batch in batches for item in batch) == candidates


def test_candidate_batches_rejects_non_positive_size():
    try:
        candidate_batches((make_candidate("a", "b"),), 0)
    except ValueError as exc:
        assert "greater than zero" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_conflict_hint_prioritizes_negation_difference():
    neutral = make_candidate(
        "The officer described the collision.",
        "The witness described the collision.",
    )
    disputed = make_candidate(
        "The officer said there was no vehicle contact.",
        "The witness said the vehicle caused the collision.",
    )

    assert conflict_hint(disputed) > conflict_hint(neutral)


def test_conflict_hint_prioritizes_numeric_difference():
    neutral = make_candidate(
        "The ticket costs 63 euros.",
        "The ticket price is 63 euros.",
    )
    differing = make_candidate(
        "The ticket costs 63 euros.",
        "The ticket costs 67 euros.",
    )

    assert conflict_hint(differing) > conflict_hint(neutral)


def test_conflict_hint_does_not_use_candidate_score():
    normal = make_candidate(
        "One account describes the event.",
        "Another account describes the event.",
        score=0.8,
    )
    high = make_candidate(
        "One account describes the event.",
        "Another account describes the event.",
        score=0.9,
    )

    assert conflict_hint(high) == conflict_hint(normal)


def test_rank_conflict_candidates_prefers_real_negation_conflict():
    neutral = make_candidate(
        "The hearing was held on Tuesday.",
        "The court released its schedule.",
        score=1.0,
    )
    disputed = make_candidate(
        "The officer said there was no vehicle contact.",
        "The witness said the vehicle made contact.",
        score=0.66,
    )
    hybrid = HybridClaimRelationAnalyzer(
        semantic_provider=None,
        max_semantic_candidates=8,
    )

    ranked = rank_conflict_candidates(
        (neutral, disputed),
        hybrid,
        1,
    )

    assert ranked == (disputed,)


def test_rank_conflict_candidates_fills_with_non_hint_recall_lane():
    hinted = make_candidate(
        "The officer said there was no vehicle contact.",
        "The witness said the vehicle made contact.",
        score=0.66,
    )
    no_hint = make_candidate(
        "Garces-Perez said the officer's SUV rammed his vehicle.",
        "The complaint says Garces-Perez rammed an officer's vehicle.",
        score=0.66,
    )
    weak = make_candidate(
        "The hearing was held on Tuesday.",
        "The court released its schedule.",
        score=0.66,
    )
    hybrid = HybridClaimRelationAnalyzer(
        semantic_provider=None,
        max_semantic_candidates=8,
    )

    ranked = rank_conflict_candidates(
        (weak, no_hint, hinted),
        hybrid,
        2,
    )

    assert ranked[0] == hinted
    assert ranked[1] == no_hint


def test_rank_conflict_candidates_reserves_half_for_recall_lane():
    hinted = tuple(
        make_candidate(
            f"The officer said there was no contact {index}.",
            f"The witness described contact {index}.",
        )
        for index in range(4)
    )
    recall = tuple(
        make_candidate(
            f"Account alpha describes event {index}.",
            f"Account beta describes event {index}.",
        )
        for index in range(4)
    )
    hybrid = HybridClaimRelationAnalyzer(
        semantic_provider=None,
        max_semantic_candidates=8,
    )

    ranked = rank_conflict_candidates(
        hinted + recall,
        hybrid,
        4,
    )

    assert len(ranked) == 4
    assert sum(conflict_hint(item) > 0 for item in ranked) == 2
    assert sum(conflict_hint(item) == 0 for item in ranked) == 2
