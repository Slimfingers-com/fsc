from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class EvidenceKind(StrEnum):
    PRIMARY_SOURCE = "primary_source"
    OFFICIAL_DATA = "official_data"
    STUDY = "study"
    DIRECT_QUOTE = "direct_quote"
    PRESS_RELEASE = "press_release"
    INDEPENDENT_REPORTING = "independent_reporting"
    CONTEXT = "context"


class EvidenceRelationKind(StrEnum):
    SUPPORTS = "supports"
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class ClaimEvidenceInput:
    claim_id: UUID
    claim_group_id: UUID
    article_id: UUID
    source_id: UUID
    source_type: str
    claim_text: str
    normalized_claim: str
    article_title: str | None
    article_text: str
    article_url: str | None
    has_direct_quote: bool


@dataclass(frozen=True, slots=True)
class StoryEvidenceAnalysisInput:
    story_id: UUID
    language_code: str | None
    claims: tuple[ClaimEvidenceInput, ...]


@dataclass(frozen=True, slots=True)
class EvidenceItemResult:
    key: str
    claim_id: UUID
    evidence_kind: EvidenceKind
    evidence_text: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ClaimEvidenceLinkResult:
    claim_group_id: UUID
    evidence_key: str
    relation_kind: EvidenceRelationKind
    confidence: float


@dataclass(frozen=True, slots=True)
class StoryEvidenceAnalysisResult:
    evidence: tuple[EvidenceItemResult, ...]
    links: tuple[ClaimEvidenceLinkResult, ...]


class EvidenceAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def configuration(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def analyze(
        self,
        story: StoryEvidenceAnalysisInput,
    ) -> StoryEvidenceAnalysisResult:
        raise NotImplementedError
