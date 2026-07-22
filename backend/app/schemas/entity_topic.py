from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.analysis.provider import EntityType, TextPart


class MentionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mention_text: str
    confidence: float
    salience: float
    text_source: TextPart
    start_offset: int | None
    end_offset: int | None
    sentence_index: int | None


class ArticleEntityRead(BaseModel):
    id: UUID
    canonical_name: str
    entity_type: EntityType
    mentions: list[MentionRead]


class ArticleTopicRead(BaseModel):
    id: UUID
    name: str
    slug: str
    relevance: float
    confidence: float


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    canonical_name: str
    normalized_name: str
    entity_type: EntityType
    description: str | None
    aliases: list[str]
    external_ids: dict[str, str] | None


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    normalized_name: str
    slug: str
    description: str | None
    parent_topic_id: UUID | None


class PageRead(BaseModel):
    items: list[EntityRead] | list[TopicRead]
    total: int
    page: int
    page_size: int
    pages: int


class LinkedArticleRead(BaseModel):
    id: UUID
    title: str | None
    published_at: datetime | None


class EntityDetailRead(EntityRead):
    article_count: int
    latest_articles: list[LinkedArticleRead]


class TopicDetailRead(TopicRead):
    article_count: int
    latest_articles: list[LinkedArticleRead]
