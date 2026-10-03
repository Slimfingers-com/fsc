from types import SimpleNamespace
from uuid import uuid4

from app.claim_relations.provider import (
    SemanticRelationCandidate,
    SemanticRelationDecision,
    SemanticRelationKind,
    StoryClaimInput,
)
from scripts.evaluate_claim_relation_shadow import classify_batch_with_fallback


def make_claim(text: str) -> StoryClaimInput:
    return StoryClaimInput(
        claim_id=uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        normalized_claim=text.casefold(),
        claim_hash=text,
        confidence=1.0,
    )


def make_candidate(index: int) -> SemanticRelationCandidate:
    return SemanticRelationCandidate(
        story_id=uuid4(),
        language_code="en",
        left_group_key=f"left-{index}",
        right_group_key=f"right-{index}",
        left_claim=make_claim(f"left claim {index}"),
        right_claim=make_claim(f"right claim {index}"),
        candidate_score=0.9,
    )
class FakeProvider:
    def __init__(self) -> None:
        self.last_usage = None
        self.batch_sizes: list[int] = []

    def classify(self, candidates):
        self.batch_sizes.append(len(candidates))
        decisions = tuple(
            SemanticRelationDecision(
                left_group_key=item.left_group_key,
                right_group_key=item.right_group_key,
                relation_kind=SemanticRelationKind.UNRELATED,
                confidence=0.9,
            )
            for item in candidates[:1]
        )
        self.last_usage = SimpleNamespace(
            input_tokens=len(candidates) * 10,
            output_tokens=len(decisions) * 2,
        )
        return decisions


class FakeHybrid:
    @staticmethod
    def validate_decisions(candidates, decisions) -> None:
        expected = {
            tuple(sorted((item.left_group_key, item.right_group_key)))
            for item in candidates
        }
        actual = {
            tuple(sorted((item.left_group_key, item.right_group_key)))
            for item in decisions
        }
        if expected != actual:
            raise ValueError(
                "semantic relation provider must classify every candidate"
            )


def test_incomplete_batch_is_split_until_complete():
    provider = FakeProvider()
    candidates = tuple(make_candidate(index) for index in range(4))

    decisions, input_tokens, output_tokens = classify_batch_with_fallback(
        provider=provider,
        hybrid=FakeHybrid(),
        candidates=candidates,
    )

    assert len(decisions) == 4
    assert provider.batch_sizes == [4, 2, 1, 1, 2, 1, 1]
    assert input_tokens == 120
    assert output_tokens == 14
