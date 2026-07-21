from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.analysis.provider import EntityType
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article


class Entity(BaseModel):
    __tablename__ = "entities"
    __table_args__ = (
        Index("uq_entities_active_name_type", "normalized_name", "entity_type", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_entities_aliases_gin", "aliases", postgresql_using="gin"),
    )
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    external_ids: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    article_mentions: Mapped[list["ArticleEntity"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class ArticleEntity(BaseModel):
    __tablename__ = "article_entities"
    __table_args__ = (
        UniqueConstraint("article_id", "entity_id", "normalized_mention", "start_offset", "end_offset", name="uq_article_entity_mention", postgresql_nulls_not_distinct=True),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_article_entities_confidence"),
        CheckConstraint("salience BETWEEN 0 AND 1", name="ck_article_entities_salience"),
    )
    article_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False, index=True)
    mention_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_mention: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type", create_type=False), nullable=False, index=True)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    sentence_index: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(nullable=False)
    salience: Mapped[float] = mapped_column(nullable=False)
    extraction_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[Entity] = relationship(back_populates="article_mentions")
    article: Mapped["Article"] = relationship(back_populates="entity_mentions")
