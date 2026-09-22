from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.analysis.provider import TextPart
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.article_processing import ArticleProcessingRun


class ArticleClaim(BaseModel):
    __tablename__ = "article_claims"

    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_hash",
            name="uq_article_claims_run_hash",
        ),
        Index(
            "uq_article_claims_active_article_hash",
            "article_id",
            "claim_hash",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL"
            ),
        ),
        Index(
            "ix_article_claims_active_article_order",
            "article_id",
            "text_source",
            "sentence_index",
            "start_offset",
            postgresql_where=text(
                "deleted_at IS NULL"
            ),
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_article_claims_confidence",
        ),
        CheckConstraint(
            "start_offset >= 0",
            name="ck_article_claims_start_offset",
        ),
        CheckConstraint(
            "end_offset > start_offset",
            name="ck_article_claims_end_offset",
        ),
        CheckConstraint(
            "sentence_index >= 0",
            name="ck_article_claims_sentence_index",
        ),
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
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_claim: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    claim_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    text_source: Mapped[TextPart] = mapped_column(
        Enum(
            TextPart,
            name="article_text_part",
        ),
        nullable=False,
        index=True,
    )

    start_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    sentence_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )

    extraction_provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    extraction_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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

    article: Mapped["Article"] = relationship(
        back_populates="claims",
    )
    processing_run: Mapped[
        "ArticleProcessingRun"
    ] = relationship()
