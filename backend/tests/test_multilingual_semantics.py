from uuid import uuid4

import pytest

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
    ClaimRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimInput,
)
from app.claim_relations.rule_based import RuleBasedClaimRelationAnalyzer
from app.clustering.provider import StoryCandidate, StoryClusteringInput
from app.clustering.rule_based import RuleBasedStoryClusterer
from app.semantic.provider import EmbeddingProvider, cosine_similarity


def test_cosine_similarity_handles_equal_and_orthogonal_vectors():
    assert cosine_similarity((1.0, 0.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)


def test_story_clusterer_matches_cross_language_semantic_candidate():
    article_id = uuid4()
    story_id = uuid4()
    candidate_article_id = uuid4()
    membership_id = uuid4()

    article = StoryClusteringInput(
        article_id=article_id,
        language_code="de",
        article_time=__import__("datetime").datetime(
            2026, 9, 22, 12, 0,
            tzinfo=__import__("datetime").UTC,
        ),
        title_terms=("haushalt", "bundestag"),
        entity_ids=(),
        topic_ids=(),
        semantic_embedding=(1.0, 0.0, 0.0),
        semantic_model="test-multilingual",
    )
    candidate = StoryCandidate(
        story_id=story_id,
        membership_id=membership_id,
        article_id=candidate_article_id,
        article_time=__import__("datetime").datetime(
            2026, 9, 22, 11, 0,
            tzinfo=__import__("datetime").UTC,
        ),
        title_terms=("budget", "parliament"),
        entity_ids=(),
        topic_ids=(),
        language_code="en",
        semantic_embedding=(0.99, 0.05, 0.0),
        semantic_model="test-multilingual",
    )

    clusterer = RuleBasedStoryClusterer(
        min_similarity=0.45,
        semantic_similarity_threshold=0.7,
    )
    result = clusterer.cluster(article, (candidate,))

    assert result.story_id == story_id
    assert result.similarity_score > 0.99
    assert result.details["semantic_model"] == "test-multilingual"


def _claim(
    *,
    text: str,
    vector: tuple[float, ...],
) -> StoryClaimInput:
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        normalized_claim=text.casefold(),
        claim_hash=uuid4().hex,
        confidence=0.9,
        semantic_embedding=vector,
        semantic_model="test-multilingual",
    )


def test_claim_relations_group_cross_language_semantic_equivalents():
    first = _claim(
        text="The government approved the budget.",
        vector=(1.0, 0.0, 0.0),
    )
    second = _claim(
        text="Die Regierung billigte den Haushalt.",
        vector=(0.99, 0.05, 0.0),
    )

    analyzer = RuleBasedClaimRelationAnalyzer(
        group_similarity_threshold=0.8,
        contradiction_similarity_threshold=0.8,
    )
    result = analyzer.analyze(
        StoryClaimAnalysisInput(
            story_id=uuid4(),
            language_code="mul",
            claims=(first, second),
        )
    )

    assert len(result.groups) == 1
    assert len(result.groups[0].members) == 2
    assert (
        result.groups[0].members[1].match_kind
        == ClaimGroupMatchKind.SEMANTIC
    )


def test_claim_relations_detect_cross_language_negation_contradiction():
    positive = _claim(
        text="The plan starts on Monday.",
        vector=(1.0, 0.0, 0.0),
    )
    negative = _claim(
        text="Der Plan startet nicht am Montag.",
        vector=(0.99, 0.04, 0.0),
    )

    analyzer = RuleBasedClaimRelationAnalyzer(
        group_similarity_threshold=0.8,
        contradiction_similarity_threshold=0.8,
    )
    result = analyzer.analyze(
        StoryClaimAnalysisInput(
            story_id=uuid4(),
            language_code="mul",
            claims=(positive, negative),
        )
    )

    assert len(result.groups) == 2
    assert len(result.relations) == 1
    assert result.relations[0].relation_kind == ClaimRelationKind.CONTRADICTS
    assert result.relations[0].confidence > 0.99
