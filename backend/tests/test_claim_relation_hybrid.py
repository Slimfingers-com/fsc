from uuid import uuid4

from app.claim_relations.hybrid import HybridClaimRelationAnalyzer
from app.claim_relations.provider import (
    ClaimRelationKind,
    SemanticClaimRelationProvider,
    SemanticRelationDecision,
    SemanticRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimInput,
)


class FakeSemanticProvider(SemanticClaimRelationProvider):
    provider = "fake-semantic"
    version = "1"

    def __init__(
        self,
        *,
        relation_kind=SemanticRelationKind.DISPUTES,
        confidence=0.95,
        fail=False,
    ):
        self.relation_kind = relation_kind
        self.confidence = confidence
        self.fail = fail
        self.calls = []

    def configuration(self):
        return {"mode": "test"}

    def classify(self, candidates):
        self.calls.append(candidates)
        if self.fail:
            raise RuntimeError("semantic provider unavailable")
        return tuple(
            SemanticRelationDecision(
                left_group_key=item.left_group_key,
                right_group_key=item.right_group_key,
                relation_kind=self.relation_kind,
                confidence=self.confidence,
            )
            for item in candidates
        )


def make_claim(
    text,
    *,
    source_id=None,
    title="ICE shooting in Austin",
    context=None,
):
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=source_id or uuid4(),
        claim_text=text,
        normalized_claim=text.casefold().rstrip("."),
        claim_hash=uuid4().hex * 2,
        confidence=0.9,
        article_title=title,
        article_context=context or f"{title}\n\n{text}",
    )


def story(*claims):
    return StoryClaimAnalysisInput(
        story_id=uuid4(),
        language_code="en",
        claims=tuple(claims),
    )


def test_hybrid_adds_high_confidence_dispute():
    first = make_claim(
        "The officer said there was no vehicle contact."
    )
    second = make_claim(
        "Garces-Perez said the ICE SUV caused the collision."
    )
    provider = FakeSemanticProvider()

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
    ).analyze(story(first, second))

    assert len(result.groups) == 2
    assert len(result.relations) == 1
    assert result.relations[0].relation_kind == ClaimRelationKind.DISPUTES
    assert len(provider.calls) == 1
    candidate = provider.calls[0][0]
    assert candidate.left_claim.article_context
    assert candidate.right_claim.article_context


def test_hybrid_does_not_promote_semantic_contradiction():
    first = make_claim(
        "The officer said there was no vehicle contact."
    )
    second = make_claim(
        "Garces-Perez said the ICE SUV caused the collision."
    )
    provider = FakeSemanticProvider(
        relation_kind=SemanticRelationKind.CONTRADICTS,
        confidence=0.99,
    )

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
    ).analyze(story(first, second))

    assert result.relations == ()


def test_hybrid_preserves_deterministic_contradiction():
    first = make_claim(
        "The climate plan will begin Monday."
    )
    second = make_claim(
        "The climate plan will not begin Monday."
    )
    provider = FakeSemanticProvider()

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
    ).analyze(story(first, second))

    assert len(result.relations) == 1
    assert (
        result.relations[0].relation_kind
        == ClaimRelationKind.CONTRADICTS
    )
    assert provider.calls == []


def test_hybrid_provider_failure_falls_back_to_rules():
    first = make_claim(
        "The officer said there was no vehicle contact."
    )
    second = make_claim(
        "Garces-Perez said the ICE SUV caused the collision."
    )
    provider = FakeSemanticProvider(fail=True)

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
    ).analyze(story(first, second))

    assert len(result.groups) == 2
    assert result.relations == ()


def test_hybrid_does_not_send_single_source_pair():
    source_id = uuid4()
    first = make_claim(
        "The officer said there was no vehicle contact.",
        source_id=source_id,
    )
    second = make_claim(
        "Garces-Perez said the ICE SUV caused the collision.",
        source_id=source_id,
    )
    provider = FakeSemanticProvider()

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
    ).analyze(story(first, second))

    assert result.relations == ()
    assert provider.calls == []


def test_hybrid_requires_dispute_confidence_threshold():
    first = make_claim(
        "The officer said there was no vehicle contact."
    )
    second = make_claim(
        "Garces-Perez said the ICE SUV caused the collision."
    )
    provider = FakeSemanticProvider(confidence=0.70)

    result = HybridClaimRelationAnalyzer(
        semantic_provider=provider,
        dispute_confidence_threshold=0.85,
    ).analyze(story(first, second))

    assert result.relations == ()
