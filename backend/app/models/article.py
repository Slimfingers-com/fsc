from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.confirmation_role import ConfirmationRole

if TYPE_CHECKING:
    from app.models.article_processing import (
        ArticleProcessingRun,
        ArticleProcessingState,
    )
    from app.models.claim import ArticleClaim
    from app.models.entity import ArticleEntity
    from app.models.feed import Feed
    from app.models.perspective import ArticlePerspective
    from app.models.search_document import SearchDocument
    from app.models.source_dependency import ArticleProvenance
    from app.models.story import StoryArticle
    from app.models.topic import ArticleTopic


class Article(BaseModel):
    __tablename__ = "articles"

    __table_args__ = (
        UniqueConstraint(
            "feed_id",
            "identity_key",
            name="uq_articles_feed_id_identity_key",
        ),
    )

    feed_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "feeds.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    identity_type: Mapped[ArticleIdentityType] = mapped_column(
        Enum(
            ArticleIdentityType,
            name="article_identity_type",
        ),
        nullable=False,
    )

    identity_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    confirmation_role: Mapped[ConfirmationRole] = mapped_column(
        Enum(
            ConfirmationRole,
            name="article_confirmation_role",
            native_enum=False,
            length=32,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=ConfirmationRole.EDITORIAL,
    )

    guid: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    link: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    author: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    normalized_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    normalized_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    language_code: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        index=True,
    )
    word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    reading_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    normalization_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    normalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    semantic_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float),
        nullable=True,
    )
    semantic_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    semantic_input_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    semantic_embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    feed: Mapped["Feed"] = relationship(
        back_populates="articles",
    )

    search_document: Mapped["SearchDocument | None"] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        uselist=False,
    )

    entity_mentions: Mapped[list["ArticleEntity"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    topics: Mapped[list["ArticleTopic"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    story_memberships: Mapped[list["StoryArticle"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    claims: Mapped[list["ArticleClaim"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    perspectives: Mapped[list["ArticlePerspective"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    processing_states: Mapped[list["ArticleProcessingState"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    processing_runs: Mapped[list["ArticleProcessingRun"]] = relationship(
        back_populates="article",
    )
    provenance: Mapped[list["ArticleProvenance"]] = relationship(
        foreign_keys="ArticleProvenance.article_id",
        back_populates="article",
        cascade="all, delete-orphan",
    )
