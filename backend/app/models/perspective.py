from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.analysis.provider import TextPart
from app.db.base import BaseModel
from app.perspectives.provider import PerspectiveKind

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.article_processing import ArticleProcessingRun
    from app.models.claim import ArticleClaim
    from app.models.entity import Entity


class ArticlePerspective(BaseModel):
    __tablename__ = "article_perspectives"

    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_id",
            "holder_entity_id",
            "perspective_kind",
            name="uq_article_perspectives_run_claim_holder_kind",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_article_perspectives_active_attributed",
            "claim_id",
            "holder_entity_id",
            "perspective_kind",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL "
                "AND holder_entity_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_article_perspectives_active_unattributed",
            "claim_id",
            "perspective_kind",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL "
                "AND holder_entity_id IS NULL"
            ),
        ),
        Index(
            "ix_article_perspectives_active_article_order",
            "article_id",
            "claim_id",
            "perspective_kind",
            postgresql_where=text(
                "deleted_at IS NULL"
            ),
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_article_perspectives_confidence",
        ),
        CheckConstraint(
            """
            (
                holder_start_offset IS NULL
                AND holder_end_offset IS NULL
            )
            OR
            (
                holder_start_offset IS NOT NULL
                AND holder_end_offset IS NOT NULL
                AND holder_start_offset >= 0
                AND holder_end_offset > holder_start_offset
            )
            """,
            name="ck_article_perspectives_holder_offsets",
        ),
        CheckConstraint(
            "start_offset >= 0",
            name="ck_article_perspectives_start_offset",
        ),
        CheckConstraint(
            "end_offset > start_offset",
            name="ck_article_perspectives_end_offset",
        ),
        CheckConstraint(
            "sentence_index >= 0",
            name="ck_article_perspectives_sentence_index",
        ),
        CheckConstraint(
            """
            (
                perspective_kind = 'UNATTRIBUTED'
                AND holder_entity_id IS NULL
                AND holder_text IS NULL
                AND holder_start_offset IS NULL
                AND holder_end_offset IS NULL
            )
            OR
            (
                perspective_kind IN ('QUOTED', 'REPORTED')
                AND holder_entity_id IS NOT NULL
                AND holder_text IS NOT NULL
                AND holder_start_offset IS NOT NULL
                AND holder_end_offset IS NOT NULL
            )
            """,
            name="ck_article_perspectives_holder_by_kind",
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
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "article_claims.id",
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
    holder_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "entities.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    holder_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    holder_start_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    holder_end_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    perspective_kind: Mapped[PerspectiveKind] = mapped_column(
        Enum(
            PerspectiveKind,
            name="perspective_kind",
        ),
        nullable=False,
        index=True,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    text_source: Mapped[TextPart] = mapped_column(
        Enum(
            TextPart,
            name="article_text_part",
            create_type=False,
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

    analysis_provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    analysis_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    article: Mapped["Article"] = relationship(
        back_populates="perspectives",
    )
    claim: Mapped["ArticleClaim"] = relationship()
    holder_entity: Mapped["Entity | None"] = relationship()
    processing_run: Mapped[
        "ArticleProcessingRun"
    ] = relationship()
