from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article


class Topic(BaseModel):
    __tablename__ = "topics"
    __table_args__ = (
        Index("uq_topics_active_normalized_name", "normalized_name", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("uq_topics_active_slug", "slug", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    parent_topic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), index=True)
    parent: Mapped["Topic | None"] = relationship(remote_side="Topic.id")
    article_topics: Mapped[list["ArticleTopic"]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class ArticleTopic(BaseModel):
    __tablename__ = "article_topics"
    __table_args__ = (
        UniqueConstraint("article_id", "topic_id", name="uq_article_topics_article_topic"),
        CheckConstraint("relevance BETWEEN 0 AND 1", name="ck_article_topics_relevance"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_article_topics_confidence"),
    )
    article_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True)
    relevance: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    detection_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_version: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[Topic] = relationship(back_populates="article_topics")
    article: Mapped["Article"] = relationship(back_populates="topics")
