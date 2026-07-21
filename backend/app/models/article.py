from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.article_identity_type import ArticleIdentityType

if TYPE_CHECKING:
    from app.models.feed import Feed


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
        ForeignKey("feeds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    identity_type: Mapped[ArticleIdentityType] = mapped_column(
        Enum(ArticleIdentityType, name="article_identity_type"),
        nullable=False,
    )

    identity_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    guid: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    feed: Mapped["Feed"] = relationship(back_populates="articles")
