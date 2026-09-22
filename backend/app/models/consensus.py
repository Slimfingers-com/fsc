from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.consensus.provider import ConsensusKind, DifferenceKind
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.claim_relation import StoryClaimGroup, StoryClaimRelation
    from app.models.story import Story
    from app.models.story_processing import StoryProcessingRun


class StoryConsensusSummary(BaseModel):
    __tablename__ = "story_consensus_summaries"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_group_id",
            name="uq_story_consensus_run_group",
        ),
        Index(
            "uq_story_consensus_active_group",
            "story_id",
            "claim_group_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "consensus_kind IN ('single_source', 'shared')",
            name="ck_story_consensus_kind",
        ),
        CheckConstraint(
            "claim_count >= 1 AND article_count >= 1 "
            "AND independent_source_count >= 1 "
            "AND evidence_item_count >= 0 "
            "AND evidence_source_count >= 0 "
            "AND attributed_perspective_count >= 0",
            name="ck_story_consensus_counts",
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
    consensus_kind: Mapped[ConsensusKind] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    claim_count: Mapped[int] = mapped_column(Integer, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attributed_perspective_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
    claim_group: Mapped["StoryClaimGroup"] = relationship()


class StoryDifferenceSummary(BaseModel):
    __tablename__ = "story_difference_summaries"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_relation_id",
            name="uq_story_difference_run_relation",
        ),
        Index(
            "uq_story_difference_active_relation",
            "story_id",
            "claim_relation_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "difference_kind = 'contradiction'",
            name="ck_story_difference_kind",
        ),
        CheckConstraint(
            "left_group_id <> right_group_id",
            name="ck_story_difference_distinct_groups",
        ),
        CheckConstraint(
            "left_independent_source_count >= 1 "
            "AND right_independent_source_count >= 1 "
            "AND left_evidence_source_count >= 0 "
            "AND right_evidence_source_count >= 0",
            name="ck_story_difference_counts",
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
    claim_relation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_claim_relations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    left_group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_claim_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    right_group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_claim_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    difference_kind: Mapped[DifferenceKind] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    left_independent_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    right_independent_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    left_evidence_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    right_evidence_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
    claim_relation: Mapped["StoryClaimRelation"] = relationship()
