import re
from difflib import SequenceMatcher

from app.semantic.provider import cosine_similarity
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
    "ne", "pas", "jamais", "aucun", "aucune",
    "no", "nunca", "ningun", "ningún", "ninguna",
    "non", "mai", "nessun", "nessuna",
    "niet", "geen", "nooit",
    "nie", "żaden", "zadna", "żadna",
}
_SEMANTIC_GROUPING_META = (
    re.compile(r"^\s*read in full\s*:", re.IGNORECASE),
    re.compile(r"\bappeared first on\b", re.IGNORECASE),
    re.compile(r"^\s*the post\b", re.IGNORECASE),
)
_RELATIVE_TIME = (
    re.compile(r"\b(today|heute)\b", re.IGNORECASE),
    re.compile(r"\b(yesterday|gestern)\b", re.IGNORECASE),
    re.compile(r"\b(tomorrow|morgen)\b", re.IGNORECASE),
    re.compile(
        r"\b(this\s+week|diese[rns]?\s+woche)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(next\s+week|nächste[nrsm]?\s+woche|naechste[nrsm]?\s+woche)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(last\s+week|letzte[nrsm]?\s+woche)\b",
        re.IGNORECASE,
    ),
)


class RuleBasedClaimRelationAnalyzer(ClaimRelationAnalyzer):
    provider = "local-rules"
    version = "2.2.0"

    def __init__(
        self,
        *,
        group_similarity_threshold: float = 0.82,
        semantic_group_similarity_threshold: float = 0.82,
        semantic_group_lexical_floor: float = 0.35,
        contradiction_similarity_threshold: float = 0.82,
    ) -> None:
        for name, value in (
            ("group_similarity_threshold", group_similarity_threshold),
            (
                "semantic_group_similarity_threshold",
                semantic_group_similarity_threshold,
            ),
            ("semantic_group_lexical_floor", semantic_group_lexical_floor),
            ("contradiction_similarity_threshold", contradiction_similarity_threshold),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")
        self.group_similarity_threshold = group_similarity_threshold
        self.semantic_group_similarity_threshold = (
            semantic_group_similarity_threshold
        )
        self.semantic_group_lexical_floor = semantic_group_lexical_floor
        self.contradiction_similarity_threshold = contradiction_similarity_threshold

    def configuration(self) -> dict[str, object]:
        return {
            "group_similarity_threshold": self.group_similarity_threshold,
            "semantic_group_similarity_threshold": (
                self.semantic_group_similarity_threshold
            ),
            "semantic_group_lexical_floor": self.semantic_group_lexical_floor,
            "contradiction_similarity_threshold": self.contradiction_similarity_threshold,
        }

    @staticmethod
    def _tokens(value: str) -> tuple[str, ...]:
        return tuple(token.casefold() for token in _TOKEN.findall(value))

    @classmethod
    def _is_negation(cls, token: str) -> bool:
        return token in _NEGATIONS or token.endswith("n't")

    @classmethod
    def _features(
        cls,
        value: str,
    ) -> tuple[frozenset[str], tuple[str, ...], bool, tuple[str, ...]]:
        tokens = cls._tokens(value)
        negative = any(cls._is_negation(token) for token in tokens)
        ordered_content = tuple(
            token
            for token in tokens
            if token not in _STOP and not cls._is_negation(token)
        )
        content = frozenset(ordered_content)
        numbers = tuple(
            match.group(0).replace(",", ".")
            for match in _NUMBER.finditer(value.casefold())
        )
        return content, ordered_content, negative, numbers

    @staticmethod
    def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @classmethod
    def _same_proposition_content(
        cls,
        left: StoryClaimInput,
        right: StoryClaimInput,
    ) -> bool:
        left_content, _, _, _ = cls._features(
            left.normalized_claim
        )
        right_content, _, _, _ = cls._features(
            right.normalized_claim
        )
        return left_content == right_content

    @classmethod
    def _similarity_components(
        cls,
        left: StoryClaimInput,
        right: StoryClaimInput,
    ) -> tuple[float, float, bool, bool, bool]:
        (
            left_tokens,
            left_ordered,
            left_negative,
            left_numbers,
        ) = cls._features(left.normalized_claim)
        (
            right_tokens,
            right_ordered,
            right_negative,
            right_numbers,
        ) = cls._features(right.normalized_claim)
        if left_numbers != right_numbers:
            return 0.0, 0.0, left_negative, right_negative, False

        lexical_score = cls._jaccard(left_tokens, right_tokens)
        order_score = SequenceMatcher(
            None,
            left_ordered,
            right_ordered,
            autojunk=False,
        ).ratio()
        lexical_similarity = min(lexical_score, order_score)

        semantic_similarity = 0.0
        if (
            left.semantic_embedding
            and right.semantic_embedding
            and left.semantic_model
            and left.semantic_model == right.semantic_model
        ):
            semantic_similarity = max(
                0.0,
                cosine_similarity(
                    left.semantic_embedding,
                    right.semantic_embedding,
                ),
            )

        return (
            lexical_similarity,
            semantic_similarity,
            left_negative,
            right_negative,
            True,
        )

    @classmethod
    def _similarity(
        cls,
        left: StoryClaimInput,
        right: StoryClaimInput,
    ) -> tuple[float, bool, bool, bool]:
        (
            lexical_similarity,
            semantic_similarity,
            left_negative,
            right_negative,
            comparable,
        ) = cls._similarity_components(left, right)
        if not comparable:
            return 0.0, left_negative, right_negative, False

        semantic_used = semantic_similarity > lexical_similarity
        return (
            max(lexical_similarity, semantic_similarity),
            left_negative,
            right_negative,
            semantic_used,
        )

    @staticmethod
    def _semantic_grouping_noise(value: str) -> bool:
        return any(pattern.search(value) for pattern in _SEMANTIC_GROUPING_META)

    @staticmethod
    def _relative_time_markers(value: str) -> frozenset[int]:
        return frozenset(
            index
            for index, pattern in enumerate(_RELATIVE_TIME)
            if pattern.search(value)
        )

    def _group_match(
        self,
        left: StoryClaimInput,
        right: StoryClaimInput,
        *,
        cross_language: bool,
    ) -> tuple[float, ClaimGroupMatchKind] | None:
        (
            lexical_similarity,
            semantic_similarity,
            left_negative,
            right_negative,
            comparable,
        ) = self._similarity_components(left, right)
        if not comparable or left_negative != right_negative:
            return None

        if lexical_similarity >= self.group_similarity_threshold:
            return lexical_similarity, ClaimGroupMatchKind.LEXICAL

        if semantic_similarity < self.semantic_group_similarity_threshold:
            return None

        if cross_language:
            return semantic_similarity, ClaimGroupMatchKind.SEMANTIC

        if lexical_similarity < self.semantic_group_lexical_floor:
            return None
        if (
            self._semantic_grouping_noise(left.claim_text)
            or self._semantic_grouping_noise(right.claim_text)
        ):
            return None
        if (
            self._relative_time_markers(left.claim_text)
            != self._relative_time_markers(right.claim_text)
        ):
            return None

        return semantic_similarity, ClaimGroupMatchKind.SEMANTIC

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
                    match = self._group_match(
                        claim,
                        representative,
                        cross_language=(story.language_code == "mul"),
                    )
                    if match is None:
                        continue
                    score, kind = match

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
                (
                    score,
                    left_negative,
                    right_negative,
                    semantic_used,
                ) = self._similarity(
                    representatives[left.key],
                    representatives[right.key],
                )
                same_proposition = self._same_proposition_content(
                    representatives[left.key],
                    representatives[right.key],
                )
                cross_language_semantic_proposition = (
                    story.language_code == "mul"
                    and semantic_used
                )
                if (
                    left_negative != right_negative
                    and score >= self.contradiction_similarity_threshold
                    and (
                        same_proposition
                        or cross_language_semantic_proposition
                    )
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
