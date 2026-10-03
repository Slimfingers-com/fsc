from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ClaimGroupMatchKind(StrEnum):
    EXACT = "exact"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"


class ClaimRelationKind(StrEnum):
    CONTRADICTS = "contradicts"
    DISPUTES = "disputes"


class SemanticRelationKind(StrEnum):
    EQUIVALENT = "equivalent"
    CONTRADICTS = "contradicts"
    DISPUTES = "disputes"
    UNRELATED = "unrelated"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class StoryClaimInput:
    claim_id: UUID
    article_id: UUID
    source_id: UUID
    claim_text: str
    normalized_claim: str
    claim_hash: str
    confidence: float
    semantic_embedding: tuple[float, ...] | None = None
    semantic_model: str | None = None
    article_title: str | None = None
    article_context: str | None = None


@dataclass(frozen=True, slots=True)
class StoryClaimAnalysisInput:
    story_id: UUID
    language_code: str | None
    claims: tuple[StoryClaimInput, ...]


@dataclass(frozen=True, slots=True)
class ClaimGroupMemberResult:
    claim_id: UUID
    similarity_score: float
    match_kind: ClaimGroupMatchKind


@dataclass(frozen=True, slots=True)
class ClaimGroupResult:
    key: str
    representative_claim_id: UUID
    members: tuple[ClaimGroupMemberResult, ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class ClaimGroupRelationResult:
    left_group_key: str
    right_group_key: str
    relation_kind: ClaimRelationKind
    confidence: float


@dataclass(frozen=True, slots=True)
class StoryClaimAnalysisResult:
    groups: tuple[ClaimGroupResult, ...]
    relations: tuple[ClaimGroupRelationResult, ...]


@dataclass(frozen=True, slots=True)
class SemanticRelationCandidate:
    story_id: UUID
    language_code: str | None
    left_group_key: str
    right_group_key: str
    left_claim: StoryClaimInput
    right_claim: StoryClaimInput
    candidate_score: float


@dataclass(frozen=True, slots=True)
class SemanticRelationDecision:
    left_group_key: str
    right_group_key: str
    relation_kind: SemanticRelationKind
    confidence: float
    reason: str | None = None


class SemanticClaimRelationProvider(ABC):
    provider: str
    version: str

    @abstractmethod
    def configuration(self) -> dict[str, object]: ...

    @abstractmethod
    def classify(
        self,
        candidates: tuple[SemanticRelationCandidate, ...],
    ) -> tuple[SemanticRelationDecision, ...]: ...


class ClaimRelationAnalyzer(ABC):
    provider: str
    version: str
    uses_article_context = False

    @abstractmethod
    def configuration(self) -> dict[str, object]: ...

    @abstractmethod
    def analyze(self, story: StoryClaimAnalysisInput) -> StoryClaimAnalysisResult: ...
