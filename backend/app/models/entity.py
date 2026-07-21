from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.analysis.provider import EntityType, TextPart
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article


class Entity(BaseModel):
    __tablename__ = "entities"
    __table_args__ = (
        Index("uq_entities_active_name_type", "normalized_name", "entity_type", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    external_ids: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    aliases: Mapped[list["EntityAlias"]] = relationship(back_populates="entity", cascade="all, delete-orphan", order_by="EntityAlias.normalized_alias")
    article_mentions: Mapped[list["ArticleEntity"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class EntityAlias(BaseModel):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        Index("ix_entity_alias_lookup", "normalized_alias", "entity_type"),
        Index("uq_entity_aliases_active_entity_alias", "entity_id", "normalized_alias", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    original_alias: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type", create_type=False), nullable=False, index=True)
    entity: Mapped[Entity] = relationship(back_populates="aliases")


class ArticleEntity(BaseModel):
    __tablename__ = "article_entities"
    __table_args__ = (
        UniqueConstraint("article_id", "entity_id", "text_source", "normalized_mention", "start_offset", "end_offset", name="uq_article_entity_mention", postgresql_nulls_not_distinct=True),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_article_entities_confidence"),
        CheckConstraint("salience BETWEEN 0 AND 1", name="ck_article_entities_salience"),
        CheckConstraint("start_offset IS NULL OR start_offset >= 0", name="ck_article_entities_start_offset"),
        CheckConstraint("end_offset IS NULL OR end_offset > start_offset", name="ck_article_entities_end_offset"),
        CheckConstraint("(start_offset IS NULL) = (end_offset IS NULL)", name="ck_article_entities_offsets_pair"),
        CheckConstraint("sentence_index IS NULL OR sentence_index >= 0", name="ck_article_entities_sentence_index"),
    )
    article_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False, index=True)
    mention_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_mention: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type", create_type=False), nullable=False, index=True)
    text_source: Mapped[TextPart] = mapped_column(Enum(TextPart, name="article_text_part"), nullable=False, index=True)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    sentence_index: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(nullable=False)
    salience: Mapped[float] = mapped_column(nullable=False)
    extraction_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[Entity] = relationship(back_populates="article_mentions")
    article: Mapped["Article"] = relationship(back_populates="entity_mentions")
