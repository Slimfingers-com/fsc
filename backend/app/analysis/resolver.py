from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.analysis.normalization import normalize_name, normalize_topic, stable_slug
from app.analysis.provider import EntityMentionResult, TopicResult
from app.repositories.entity_topic import AmbiguousEntityAliasError, EntityTopicRepository

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.topic import Topic


class EntityResolver:
    def __init__(self, repository: EntityTopicRepository | None = None, *, min_confidence: float = 0.65) -> None:
        self.repository = repository or EntityTopicRepository()
        self.min_confidence = min_confidence

    def resolve(self, db: Session, result: EntityMentionResult) -> Entity | None:
        normalized = normalize_name(result.canonical_name)
        if not normalized or result.confidence < self.min_confidence:
            return None
        try:
            entity = self.repository.find_entity(db, normalized, result.entity_type)
        except AmbiguousEntityAliasError:
            return None
        if entity:
            return entity
        return self.repository.create_or_get_entity(db, canonical_name=" ".join(result.canonical_name.split()), normalized_name=normalized, entity_type=result.entity_type)


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
        name = " ".join(result.name.split())
        slug = stable_slug(normalized)
        collision_slug = f"{slug}--{hashlib.sha256(normalized.encode()).hexdigest()[:10]}"
        return self.repository.create_or_get_topic(db, name=name, normalized_name=normalized, slug=slug, collision_slug=collision_slug)
