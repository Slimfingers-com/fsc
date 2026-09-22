from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ConsensusKind(StrEnum):
    SINGLE_SOURCE = "single_source"
    SHARED = "shared"


class DifferenceKind(StrEnum):
    CONTRADICTION = "contradiction"


@dataclass(frozen=True, slots=True)
class ClaimGroupConsensusInput:
    group_id: UUID
    representative_claim_id: UUID
    representative_claim_text: str
    claim_count: int
    article_count: int
    independent_source_count: int
    evidence_item_count: int
    evidence_source_count: int
    attributed_perspective_count: int


@dataclass(frozen=True, slots=True)
class ClaimDifferenceInput:
    relation_id: UUID
    left_group_id: UUID
    right_group_id: UUID
    left_claim_text: str
    right_claim_text: str
    left_independent_source_count: int
    right_independent_source_count: int
    left_evidence_source_count: int
    right_evidence_source_count: int


@dataclass(frozen=True, slots=True)
class StoryConsensusInput:
    story_id: UUID
    language_code: str | None
    groups: tuple[ClaimGroupConsensusInput, ...]
    differences: tuple[ClaimDifferenceInput, ...]


@dataclass(frozen=True, slots=True)
class ConsensusSummaryResult:
    group_id: UUID
    consensus_kind: ConsensusKind


@dataclass(frozen=True, slots=True)
class DifferenceSummaryResult:
    relation_id: UUID
    difference_kind: DifferenceKind


@dataclass(frozen=True, slots=True)
class StoryConsensusResult:
    consensus: tuple[ConsensusSummaryResult, ...]
    differences: tuple[DifferenceSummaryResult, ...]


class ConsensusAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def configuration(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def analyze(
        self,
        story: StoryConsensusInput,
    ) -> StoryConsensusResult:
        raise NotImplementedError
