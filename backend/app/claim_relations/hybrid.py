import logging
import math
import re
from difflib import SequenceMatcher

from app.claim_relations.provider import (
    ClaimGroupRelationResult,
    ClaimRelationAnalyzer,
    ClaimRelationKind,
    SemanticClaimRelationProvider,
    SemanticRelationCandidate,
    SemanticRelationDecision,
    SemanticRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimAnalysisResult,
    StoryClaimInput,
)
from app.claim_relations.rule_based import RuleBasedClaimRelationAnalyzer
from app.semantic.provider import cosine_similarity


logger = logging.getLogger(__name__)
_TOKEN = re.compile(r"\b[^\W_][\w'’-]*\b", re.UNICODE)


class HybridClaimRelationAnalyzer(ClaimRelationAnalyzer):
    provider = "hybrid"
    version = "1.0.0"
    uses_article_context = True

    def __init__(
        self,
        *,
        base_analyzer: RuleBasedClaimRelationAnalyzer | None = None,
        semantic_provider: SemanticClaimRelationProvider | None = None,
        candidate_similarity_threshold: float = 0.55,
        dispute_confidence_threshold: float = 0.85,
        max_semantic_candidates: int = 24,
    ) -> None:
        if not 0 <= candidate_similarity_threshold <= 1:
            raise ValueError(
                "candidate_similarity_threshold must be between zero and one"
            )
        if not 0 <= dispute_confidence_threshold <= 1:
            raise ValueError(
                "dispute_confidence_threshold must be between zero and one"
            )
        if max_semantic_candidates <= 0:
            raise ValueError("max_semantic_candidates must be greater than zero")

        self.base_analyzer = base_analyzer or RuleBasedClaimRelationAnalyzer()
        self.semantic_provider = semantic_provider
        self.candidate_similarity_threshold = candidate_similarity_threshold
        self.dispute_confidence_threshold = dispute_confidence_threshold
        self.max_semantic_candidates = max_semantic_candidates

    def configuration(self) -> dict[str, object]:
        semantic = None
        if self.semantic_provider is not None:
            semantic = {
                "provider": self.semantic_provider.provider,
                "version": self.semantic_provider.version,
                "configuration": self.semantic_provider.configuration(),
            }
        return {
            "base_provider": self.base_analyzer.provider,
            "base_version": self.base_analyzer.version,
            "base_configuration": self.base_analyzer.configuration(),
            "semantic_provider": semantic,
            "candidate_similarity_threshold": self.candidate_similarity_threshold,
            "dispute_confidence_threshold": self.dispute_confidence_threshold,
            "max_semantic_candidates": self.max_semantic_candidates,
        }

    @staticmethod
    def _tokens(value: str | None) -> tuple[str, ...]:
        if not value:
            return ()
        return tuple(token.casefold() for token in _TOKEN.findall(value))

    @classmethod
    def _text_similarity(cls, left: str | None, right: str | None) -> float:
        left_tokens = cls._tokens(left)
        right_tokens = cls._tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        left_set = frozenset(left_tokens)
        right_set = frozenset(right_tokens)
        jaccard = len(left_set & right_set) / len(left_set | right_set)
        order = SequenceMatcher(
            None,
            left_tokens,
            right_tokens,
            autojunk=False,
        ).ratio()
        return min(jaccard, order)

    @classmethod
    def _candidate_score(
        cls,
        left: StoryClaimInput,
        right: StoryClaimInput,
    ) -> float:
        lexical = cls._text_similarity(
            left.normalized_claim,
            right.normalized_claim,
        )
        title = cls._text_similarity(
            left.article_title,
            right.article_title,
        )
        semantic = 0.0
        if (
            left.semantic_embedding
            and right.semantic_embedding
            and left.semantic_model
            and left.semantic_model == right.semantic_model
        ):
            semantic = max(
                0.0,
                cosine_similarity(
                    left.semantic_embedding,
                    right.semantic_embedding,
                ),
            )
        return max(lexical, semantic, title)

    @staticmethod
    def validate_decisions(
        candidates: tuple[SemanticRelationCandidate, ...],
        decisions: tuple[SemanticRelationDecision, ...],
    ) -> None:
        expected = {
            tuple(sorted((item.left_group_key, item.right_group_key)))
            for item in candidates
        }
        seen: set[tuple[str, str]] = set()
        for item in decisions:
            if not isinstance(item.relation_kind, SemanticRelationKind):
                raise ValueError("semantic relation kind is invalid")
            if (
                not math.isfinite(item.confidence)
                or not 0 <= item.confidence <= 1
            ):
                raise ValueError(
                    "semantic relation confidence must be between zero and one"
                )
            key = tuple(sorted((item.left_group_key, item.right_group_key)))
            if key not in expected:
                raise ValueError(
                    "semantic relation decision references an unknown candidate"
                )
            if key in seen:
                raise ValueError("duplicate semantic relation decision")
            seen.add(key)
        if seen != expected:
            raise ValueError(
                "semantic relation provider must classify every candidate"
            )

    def semantic_candidates(
        self,
        story: StoryClaimAnalysisInput,
        base: StoryClaimAnalysisResult,
    ) -> tuple[SemanticRelationCandidate, ...]:
        claim_by_id = {
            item.claim_id: item
            for item in story.claims
        }
        existing_pairs = {
            tuple(sorted((item.left_group_key, item.right_group_key)))
            for item in base.relations
        }
        scored: list[tuple[float, SemanticRelationCandidate]] = []

        for left_index, left_group in enumerate(base.groups):
            left_claim = claim_by_id[left_group.representative_claim_id]
            left_sources = {
                claim_by_id[item.claim_id].source_id
                for item in left_group.members
            }
            for right_group in base.groups[left_index + 1:]:
                pair = tuple(sorted((left_group.key, right_group.key)))
                if pair in existing_pairs:
                    continue

                right_claim = claim_by_id[
                    right_group.representative_claim_id
                ]
                right_sources = {
                    claim_by_id[item.claim_id].source_id
                    for item in right_group.members
                }
                if len(left_sources | right_sources) < 2:
                    continue

                score = self._candidate_score(left_claim, right_claim)
                if score < self.candidate_similarity_threshold:
                    continue

                candidate = SemanticRelationCandidate(
                    story_id=story.story_id,
                    language_code=story.language_code,
                    left_group_key=left_group.key,
                    right_group_key=right_group.key,
                    left_claim=left_claim,
                    right_claim=right_claim,
                    candidate_score=score,
                )
                scored.append((score, candidate))

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].left_group_key,
                item[1].right_group_key,
            )
        )
        return tuple(
            item[1]
            for item in scored[: self.max_semantic_candidates]
        )

    def analyze(
        self,
        story: StoryClaimAnalysisInput,
    ) -> StoryClaimAnalysisResult:
        base = self.base_analyzer.analyze(story)
        if self.semantic_provider is None:
            return base

        candidates = self.semantic_candidates(story, base)
        if not candidates:
            return base

        try:
            decisions = self.semantic_provider.classify(candidates)
            self.validate_decisions(candidates, decisions)
        except Exception:
            logger.exception(
                "Semantic claim relation provider failed; "
                "falling back to deterministic relations",
                extra={"story_id": str(story.story_id)},
            )
            return base

        added: list[ClaimGroupRelationResult] = []
        for item in decisions:
            if (
                item.relation_kind != SemanticRelationKind.DISPUTES
                or item.confidence < self.dispute_confidence_threshold
            ):
                continue
            added.append(
                ClaimGroupRelationResult(
                    left_group_key=item.left_group_key,
                    right_group_key=item.right_group_key,
                    relation_kind=ClaimRelationKind.DISPUTES,
                    confidence=item.confidence,
                )
            )

        return StoryClaimAnalysisResult(
            groups=base.groups,
            relations=base.relations + tuple(added),
        )
