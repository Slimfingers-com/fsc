import math
from uuid import uuid4

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
    StoryClaimInput,
)
from app.claim_relations.rule_based import (
    RuleBasedClaimRelationAnalyzer,
)


def make_claim(
    text: str,
    embedding: tuple[float, float],
) -> StoryClaimInput:
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        normalized_claim=text.casefold(),
        claim_hash=uuid4().hex,
        confidence=0.9,
        semantic_embedding=embedding,
        semantic_model="test-embedding",
    )


def cosine_embedding(
    similarity: float,
) -> tuple[float, float]:
    return (
        similarity,
        math.sqrt(1 - similarity**2),
    )


def test_high_confidence_semantic_path_accepts_anchored_paraphrase():
    analyzer = RuleBasedClaimRelationAnalyzer()
    left = make_claim(
        (
            "Coast Guard suspends search for 6 missing "
            "medical jet passengers off Nantucket"
        ),
        (1.0, 0.0),
    )
    right = make_claim(
        (
            "Search suspended for 6 aboard medical flight "
            "that went missing near Nantucket: Coast Guard"
        ),
        cosine_embedding(0.84),
    )

    (
        lexical_similarity,
        semantic_similarity,
        *_,
    ) = analyzer._similarity_components(
        left,
        right,
    )
    match = analyzer._group_match(
        left,
        right,
        cross_language=False,
    )

    assert (
        analyzer.semantic_high_confidence_lexical_floor
        <= lexical_similarity
        < analyzer.semantic_group_lexical_floor
    )
    assert semantic_similarity >= 0.83
    assert match is not None
    assert match[1] is ClaimGroupMatchKind.SEMANTIC


def test_high_confidence_semantic_path_requires_lexical_anchor():
    analyzer = RuleBasedClaimRelationAnalyzer()
    left = make_claim(
        "Alpha committee approves proposal",
        (1.0, 0.0),
    )
    right = make_claim(
        "Delta agency rejects motion",
        cosine_embedding(0.95),
    )

    assert analyzer._group_match(
        left,
        right,
        cross_language=False,
    ) is None


def test_high_confidence_semantic_path_keeps_number_guard():
    analyzer = RuleBasedClaimRelationAnalyzer()
    left = make_claim(
        (
            "Coast Guard suspends search for 6 missing "
            "medical jet passengers off Nantucket"
        ),
        (1.0, 0.0),
    )
    right = make_claim(
        (
            "Search suspended for 7 aboard medical flight "
            "that went missing near Nantucket: Coast Guard"
        ),
        cosine_embedding(0.95),
    )

    assert analyzer._group_match(
        left,
        right,
        cross_language=False,
    ) is None


def test_high_confidence_semantic_path_keeps_relative_time_guard():
    analyzer = RuleBasedClaimRelationAnalyzer()
    left = make_claim(
        "Coast Guard suspends search today near Nantucket",
        (1.0, 0.0),
    )
    right = make_claim(
        "Coast Guard suspended the search yesterday near Nantucket",
        cosine_embedding(0.95),
    )

    assert analyzer._group_match(
        left,
        right,
        cross_language=False,
    ) is None
