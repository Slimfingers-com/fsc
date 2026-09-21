from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ClaimGroupMatchKind(StrEnum):
    EXACT = "exact"
    LEXICAL = "lexical"


class ClaimRelationKind(StrEnum):
    CONTRADICTS = "contradicts"


@dataclass(frozen=True, slots=True)
class StoryClaimInput:
    claim_id: UUID
    article_id: UUID
    source_id: UUID
    claim_text: str
    normalized_claim: str
    claim_hash: str
    confidence: float


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


class ClaimRelationAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def configuration(self) -> dict[str, object]: ...

    @abstractmethod
    def analyze(self, story: StoryClaimAnalysisInput) -> StoryClaimAnalysisResult: ...
