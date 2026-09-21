from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.analysis.provider import EntityType, TextPart


class PerspectiveKind(StrEnum):
    QUOTED = "quoted"
    REPORTED = "reported"
    UNATTRIBUTED = "unattributed"


@dataclass(frozen=True, slots=True)
class PerspectiveClaimInput:
    claim_id: UUID
    claim_text: str
    claim_hash: str
    text_source: TextPart
    start_offset: int
    end_offset: int
    sentence_index: int
    confidence: float


@dataclass(frozen=True, slots=True)
class PerspectiveEntityMentionInput:
    mention_id: UUID
    entity_id: UUID
    mention_text: str
    entity_type: EntityType
    text_source: TextPart
    start_offset: int | None
    end_offset: int | None
    sentence_index: int | None
    confidence: float
    salience: float


@dataclass(frozen=True, slots=True)
class PerspectiveAnalysisInput:
    article_id: UUID
    title: str
    normalized_text: str
    language_code: str | None
    claims: tuple[PerspectiveClaimInput, ...]
    entity_mentions: tuple[PerspectiveEntityMentionInput, ...]


@dataclass(frozen=True, slots=True)
class PerspectiveAttribution:
    claim_id: UUID
    perspective_kind: PerspectiveKind
    holder_mention_id: UUID | None
    evidence_text: str
    text_source: TextPart
    start_offset: int
    end_offset: int
    sentence_index: int
    confidence: float


@dataclass(frozen=True, slots=True)
class PerspectiveAnalysisResult:
    attributions: tuple[PerspectiveAttribution, ...]


class PerspectiveAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def analyze(
        self,
        article: PerspectiveAnalysisInput,
    ) -> PerspectiveAnalysisResult: ...
