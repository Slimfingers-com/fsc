from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import re
import unicodedata
from uuid import UUID

from app.analysis.provider import TextPart


_WHITESPACE = re.compile(r"\s+")


def normalize_claim_text(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        value,
    ).strip()
    normalized = normalized.rstrip(
        ".!?。！？"
    ).rstrip()
    return _WHITESPACE.sub(
        " ",
        normalized,
    ).casefold()


@dataclass(frozen=True, slots=True)
class ClaimExtractionInput:
    article_id: UUID
    title: str
    normalized_text: str
    language_code: str | None
    published_at: datetime | None
    source_metadata: dict[str, str] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class ExtractedClaim:
    claim_text: str
    text_source: TextPart
    start_offset: int
    end_offset: int
    sentence_index: int
    confidence: float


@dataclass(frozen=True, slots=True)
class ClaimExtractionResult:
    claims: tuple[ExtractedClaim, ...]


class ClaimExtractor(ABC):
    provider: str
    version: str

    @abstractmethod
    def extract(
        self,
        article: ClaimExtractionInput,
    ) -> ClaimExtractionResult: ...
