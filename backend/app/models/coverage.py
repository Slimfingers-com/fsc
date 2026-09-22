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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.coverage.provider import CoverageGapKind, MissingPerspectiveKind
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.claim_relation import StoryClaimGroup
    from app.models.story import Story
    from app.models.story_processing import StoryProcessingRun


class StoryCoverageSummary(BaseModel):
    __tablename__ = "story_coverage_summaries"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "story_id",
            name="uq_story_coverage_run_story",
        ),
        Index(
            "uq_story_coverage_active_story",
            "story_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "article_count >= 1 "
            "AND source_count >= 1 "
            "AND content_source_count >= 0 "
            "AND signal_source_count >= 0 "
            "AND independent_content_owner_count >= 0 "
            "AND claim_group_count >= 1 "
            "AND shared_group_count >= 0 "
            "AND difference_count >= 0 "
            "AND attributed_group_count >= 0",
            name="ck_story_coverage_summary_counts",
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
    consensus_processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_content_owner_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    claim_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    difference_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attributed_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    coverage_scope_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    country_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship(
        foreign_keys=[processing_run_id]
    )
    consensus_processing_run: Mapped["StoryProcessingRun"] = relationship(
        foreign_keys=[consensus_processing_run_id]
    )


class StoryCoverageGap(BaseModel):
    __tablename__ = "story_coverage_gaps"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "gap_key",
            name="uq_story_coverage_gap_run_key",
        ),
        Index(
            "uq_story_coverage_gap_active_key",
            "story_id",
            "gap_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "gap_kind IN ("
            "'limited_independent_content_sources', "
            "'signal_without_content_coverage')",
            name="ck_story_coverage_gap_kind",
        ),
        CheckConstraint(
            "observed_count >= 0 "
            "AND (minimum_expected IS NULL OR minimum_expected >= 0)",
            name="ck_story_coverage_gap_counts",
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
    gap_key: Mapped[str] = mapped_column(String(100), nullable=False)
    gap_kind: Mapped[CoverageGapKind] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    observed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_expected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship(
        foreign_keys=[processing_run_id]
    )
    consensus_processing_run: Mapped["StoryProcessingRun"] = relationship(
        foreign_keys=[consensus_processing_run_id]
    )


class StoryMissingPerspective(BaseModel):
    __tablename__ = "story_missing_perspectives"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "claim_group_id",
            "missing_kind",
            name="uq_story_missing_perspective_run_group_kind",
        ),
        Index(
            "uq_story_missing_perspective_active_group_kind",
            "story_id",
            "claim_group_id",
            "missing_kind",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "missing_kind = 'no_attributed_perspective'",
            name="ck_story_missing_perspective_kind",
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
    missing_kind: Mapped[MissingPerspectiveKind] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    contradiction_relation_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
    claim_group: Mapped["StoryClaimGroup"] = relationship()
