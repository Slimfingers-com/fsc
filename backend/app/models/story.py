from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSONB,
    UUID as PG_UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.article_processing import ArticleProcessingRun
    from app.models.story_processing import (
        StoryProcessingRun,
        StoryProcessingState,
    )


class Story(BaseModel):
    __tablename__ = "stories"

    __table_args__ = (
        Index(
            "ix_stories_active_language",
            "language_code",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    language_code: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )

    memberships: Mapped[list["StoryArticle"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    processing_states: Mapped[list["StoryProcessingState"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    processing_runs: Mapped[list["StoryProcessingRun"]] = relationship(
        back_populates="story",
    )


class StoryArticle(BaseModel):
    __tablename__ = "story_articles"

    __table_args__ = (
        Index(
            "uq_story_articles_active_article",
            "article_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_story_articles_processing_run",
            "processing_run_id",
            unique=True,
        ),
        Index(
            "ix_story_articles_active_story_time",
            "story_id",
            "article_time",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_story_articles_active_time",
            "article_time",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_story_articles_active_title_terms_gin",
            "title_terms",
            postgresql_using="gin",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_story_articles_active_entity_ids_gin",
            "entity_ids",
            postgresql_using="gin",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_story_articles_active_topic_ids_gin",
            "topic_ids",
            postgresql_using="gin",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "similarity_score BETWEEN 0 AND 1",
            name="ck_story_articles_similarity_score",
        ),
        CheckConstraint(
            "match_kind IN ('created', 'matched', 'retained')",
            name="ck_story_articles_match_kind",
        ),
    )

    story_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "stories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "article_processing_runs.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    article_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    article_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    title_terms: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )

    entity_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )

    topic_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )

    similarity_score: Mapped[float] = mapped_column(
        nullable=False,
    )

    match_kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    match_details: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    clustered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    story: Mapped[Story] = relationship(
        back_populates="memberships",
    )

    article: Mapped["Article"] = relationship(
        back_populates="story_memberships",
    )

    processing_run: Mapped["ArticleProcessingRun"] = relationship()
