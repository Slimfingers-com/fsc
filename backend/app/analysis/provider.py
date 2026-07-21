from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class EntityType(StrEnum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    PRODUCT = "product"
    OTHER = "other"


class TextPart(StrEnum):
    TITLE = "title"
    BODY = "body"


@dataclass(frozen=True, slots=True)
class ArticleAnalysisInput:
    article_id: UUID
    title: str
    normalized_text: str
    language_code: str | None
    published_at: datetime | None
    source_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EntityMentionResult:
    canonical_name: str
    mention_text: str
    entity_type: EntityType
    confidence: float
    salience: float
    text_part: TextPart
    start_offset: int | None = None
    end_offset: int | None = None
    sentence_index: int | None = None


@dataclass(frozen=True, slots=True)
class TopicResult:
    name: str
    relevance: float
    confidence: float


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    entities: tuple[EntityMentionResult, ...]
    topics: tuple[TopicResult, ...]


class EntityTopicAnalyzer(ABC):
    provider: str
    version: str

    @abstractmethod
    def analyze(self, article: ArticleAnalysisInput) -> AnalysisResult: ...
