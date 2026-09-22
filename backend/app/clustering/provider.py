from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StoryClusteringInput:
    article_id: UUID
    language_code: str | None
    article_time: datetime
    title_terms: tuple[str, ...]
    entity_ids: tuple[UUID, ...]
    topic_ids: tuple[UUID, ...]
    semantic_embedding: tuple[float, ...] | None = None
    semantic_model: str | None = None


@dataclass(frozen=True, slots=True)
class StoryCandidate:
    story_id: UUID
    membership_id: UUID
    article_id: UUID
    article_time: datetime
    title_terms: tuple[str, ...]
    entity_ids: tuple[UUID, ...]
    topic_ids: tuple[UUID, ...]
    language_code: str | None = None
    semantic_embedding: tuple[float, ...] | None = None
    semantic_model: str | None = None


@dataclass(frozen=True, slots=True)
class StoryClusteringResult:
    story_id: UUID | None
    similarity_score: float
    matched_membership_id: UUID | None
    matched_article_id: UUID | None
    details: dict[str, object]


class StoryClusterer(ABC):
    provider: str
    version: str

    def configuration(
        self,
    ) -> dict[str, object]:
        return {}

    @abstractmethod
    def cluster(
        self,
        article: StoryClusteringInput,
        candidates: tuple[StoryCandidate, ...],
    ) -> StoryClusteringResult: ...
