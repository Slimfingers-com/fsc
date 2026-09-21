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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.evidence.provider import EvidenceKind, EvidenceRelationKind

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.claim import ArticleClaim
    from app.models.claim_relation import StoryClaimGroup
    from app.models.source import Source
    from app.models.story import Story
    from app.models.story_processing import StoryProcessingRun


class StoryEvidence(BaseModel):
    __tablename__ = "story_evidence"

    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_id",
            name="uq_story_evidence_run_claim",
        ),
        Index(
            "uq_story_evidence_active_story_claim",
            "story_id",
            "claim_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_story_evidence_confidence",
        ),
        CheckConstraint(
            "evidence_kind IN ("
            "'primary_source', 'official_data', 'study', "
            "'direct_quote', 'press_release', "
            "'independent_reporting', 'context')",
            name="ck_story_evidence_kind",
        ),
    )

    story_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("article_claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_kind: Mapped[EvidenceKind] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    evidence_text: Mapped[str] = mapped_column(
        Text,
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

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
    claim: Mapped["ArticleClaim"] = relationship()
    article: Mapped["Article"] = relationship()
    source: Mapped["Source"] = relationship()
    links: Mapped[list["StoryClaimEvidence"]] = relationship(
        back_populates="evidence",
        cascade="all, delete-orphan",
    )


class StoryClaimEvidence(BaseModel):
    __tablename__ = "story_claim_evidence"

    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_group_id",
            "evidence_id",
            "relation_kind",
            name="uq_story_claim_evidence_run_group_evidence_kind",
        ),
        Index(
            "ix_story_claim_evidence_active_group",
            "claim_group_id",
            "relation_kind",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_story_claim_evidence_confidence",
        ),
        CheckConstraint(
            "relation_kind IN ('supports', 'context')",
            name="ck_story_claim_evidence_relation_kind",
        ),
    )

    story_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    claim_group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_claim_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_evidence.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_kind: Mapped[EvidenceRelationKind] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )

    evidence: Mapped[StoryEvidence] = relationship(
        back_populates="links",
    )
    claim_group: Mapped["StoryClaimGroup"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
