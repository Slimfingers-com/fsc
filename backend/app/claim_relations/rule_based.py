import re

from app.claim_relations.provider import (
    ClaimGroupMatchKind,
    ClaimGroupMemberResult,
    ClaimGroupRelationResult,
    ClaimGroupResult,
    ClaimRelationAnalyzer,
    ClaimRelationKind,
    StoryClaimAnalysisInput,
    StoryClaimAnalysisResult,
    StoryClaimInput,
)


_TOKEN = re.compile(r"\b[^\W_][\w'’-]*\b", re.UNICODE)
_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b", re.UNICODE)
_STOP = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "from",
    "with", "that", "this", "is", "are", "was", "were", "be", "been", "being",
    "der", "die", "das", "ein", "eine", "einer", "einem", "einen", "und",
    "oder", "von", "im", "in", "auf", "für", "zu", "mit", "ist", "sind",
    "war", "waren", "wird", "werden",
}
_NEGATIONS = {
    "not", "no", "never", "without", "neither", "nor",
    "nicht", "kein", "keine", "keinen", "keinem", "keiner", "nie", "niemals",
}


class RuleBasedClaimRelationAnalyzer(ClaimRelationAnalyzer):
    provider = "local-rules"
    version = "1.0.0"

    def __init__(
        self,
        *,
        group_similarity_threshold: float = 0.82,
        contradiction_similarity_threshold: float = 0.82,
    ) -> None:
        for name, value in (
            ("group_similarity_threshold", group_similarity_threshold),
            ("contradiction_similarity_threshold", contradiction_similarity_threshold),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")
        self.group_similarity_threshold = group_similarity_threshold
        self.contradiction_similarity_threshold = contradiction_similarity_threshold

    def configuration(self) -> dict[str, object]:
        return {
            "group_similarity_threshold": self.group_similarity_threshold,
            "contradiction_similarity_threshold": self.contradiction_similarity_threshold,
        }

    @staticmethod
    def _tokens(value: str) -> tuple[str, ...]:
        return tuple(token.casefold() for token in _TOKEN.findall(value))

    @classmethod
    def _is_negation(cls, token: str) -> bool:
        return token in _NEGATIONS or token.endswith("n't")

    @classmethod
    def _features(cls, value: str) -> tuple[frozenset[str], bool, tuple[str, ...]]:
        tokens = cls._tokens(value)
        negative = any(cls._is_negation(token) for token in tokens)
        content = frozenset(
            token
            for token in tokens
            if token not in _STOP and not cls._is_negation(token)
        )
        numbers = tuple(
            match.group(0).replace(",", ".")
            for match in _NUMBER.finditer(value.casefold())
        )
        return content, negative, numbers

    @staticmethod
    def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @classmethod
    def _similarity(
        cls,
        left: StoryClaimInput,
        right: StoryClaimInput,
    ) -> tuple[float, bool, bool]:
        left_tokens, left_negative, left_numbers = cls._features(left.normalized_claim)
        right_tokens, right_negative, right_numbers = cls._features(right.normalized_claim)
        if left_numbers != right_numbers:
            return 0.0, left_negative, right_negative
        return cls._jaccard(left_tokens, right_tokens), left_negative, right_negative

    def analyze(self, story: StoryClaimAnalysisInput) -> StoryClaimAnalysisResult:
        claims = sorted(
            story.claims,
            key=lambda item: (item.normalized_claim, str(item.article_id), str(item.claim_id)),
        )
        working: list[dict[str, object]] = []

        for claim in claims:
            best_index: int | None = None
            best_score = -1.0
            best_kind = ClaimGroupMatchKind.LEXICAL

            for index, group in enumerate(working):
                representative = group["representative"]
                assert isinstance(representative, StoryClaimInput)
                if claim.normalized_claim == representative.normalized_claim:
                    score = 1.0
                    kind = ClaimGroupMatchKind.EXACT
                else:
                    score, claim_negative, representative_negative = self._similarity(
                        claim,
                        representative,
                    )
                    if claim_negative != representative_negative:
                        continue
                    if score < self.group_similarity_threshold:
                        continue
                    kind = ClaimGroupMatchKind.LEXICAL

                if score > best_score:
                    best_index = index
                    best_score = score
                    best_kind = kind

            member = ClaimGroupMemberResult(
                claim_id=claim.claim_id,
                similarity_score=best_score if best_index is not None else 1.0,
                match_kind=best_kind if best_index is not None else ClaimGroupMatchKind.EXACT,
            )
            if best_index is None:
                working.append({"representative": claim, "members": [member]})
            else:
                members = working[best_index]["members"]
                assert isinstance(members, list)
                members.append(member)

        groups: list[ClaimGroupResult] = []
        representatives: dict[str, StoryClaimInput] = {}
        for index, group in enumerate(working, start=1):
            representative = group["representative"]
            members = group["members"]
            assert isinstance(representative, StoryClaimInput)
            assert isinstance(members, list)
            key = f"group-{index:04d}"
            typed_members = tuple(members)
            groups.append(
                ClaimGroupResult(
                    key=key,
                    representative_claim_id=representative.claim_id,
                    members=typed_members,
                    confidence=min(member.similarity_score for member in typed_members),
                )
            )
            representatives[key] = representative

        relations: list[ClaimGroupRelationResult] = []
        for left_index, left in enumerate(groups):
            for right in groups[left_index + 1:]:
                score, left_negative, right_negative = self._similarity(
                    representatives[left.key],
                    representatives[right.key],
                )
                if (
                    left_negative != right_negative
                    and score >= self.contradiction_similarity_threshold
                ):
                    relations.append(
                        ClaimGroupRelationResult(
                            left_group_key=left.key,
                            right_group_key=right.key,
                            relation_kind=ClaimRelationKind.CONTRADICTS,
                            confidence=score,
                        )
                    )

        return StoryClaimAnalysisResult(
            groups=tuple(groups),
            relations=tuple(relations),
        )
