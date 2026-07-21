from sqlalchemy.orm import Session

from app.analysis.normalization import normalize_name, normalize_topic, stable_slug
from app.analysis.provider import EntityMentionResult, TopicResult
from app.models.entity import Entity
from app.models.topic import Topic
from app.repositories.entity_topic import EntityTopicRepository


class EntityResolver:
    def __init__(self, repository: EntityTopicRepository | None = None, *, min_confidence: float = 0.65) -> None:
        self.repository = repository or EntityTopicRepository()
        self.min_confidence = min_confidence

    def resolve(self, db: Session, result: EntityMentionResult) -> Entity | None:
        normalized = normalize_name(result.canonical_name)
        if not normalized or result.confidence < self.min_confidence:
            return None
        entity = self.repository.find_entity(db, normalized, result.entity_type)
        if entity:
            return entity
        entity = Entity(canonical_name=" ".join(result.canonical_name.split()), normalized_name=normalized, entity_type=result.entity_type, aliases=[])
        db.add(entity)
        db.flush()
        return entity


class TopicResolver:
    GENERIC = {"news", "article", "today", "people", "thing", "nachricht", "heute", "bericht"}

    def __init__(self, repository: EntityTopicRepository | None = None, *, min_confidence: float = 0.6) -> None:
        self.repository = repository or EntityTopicRepository()
        self.min_confidence = min_confidence

    def resolve(self, db: Session, result: TopicResult) -> Topic | None:
        normalized = normalize_topic(result.name)
        if len(normalized) < 4 or normalized in self.GENERIC or result.confidence < self.min_confidence:
            return None
        topic = self.repository.find_topic(db, normalized)
        if topic:
            return topic
        topic = Topic(name=" ".join(result.name.split()), normalized_name=normalized, slug=stable_slug(normalized))
        db.add(topic)
        db.flush()
        return topic
