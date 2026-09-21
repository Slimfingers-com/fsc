from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.claim_relations.provider import ClaimGroupMatchKind, ClaimRelationKind
from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.claim import ArticleClaim
    from app.models.story import Story
    from app.models.story_processing import StoryProcessingRun


class StoryClaimGroup(BaseModel):
    __tablename__ = "story_claim_groups"
    __table_args__ = (
        UniqueConstraint("processing_run_id", "group_hash", name="uq_story_claim_groups_run_hash"),
        Index(
            "uq_story_claim_groups_active_story_hash",
            "story_id",
            "group_hash",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_story_claim_groups_confidence"),
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
    representative_claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("article_claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    story: Mapped["Story"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()
    representative_claim: Mapped["ArticleClaim"] = relationship(
        foreign_keys=[representative_claim_id]
    )
    members: Mapped[list["StoryClaimGroupMember"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )


class StoryClaimGroupMember(BaseModel):
    __tablename__ = "story_claim_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "claim_id", name="uq_story_claim_group_members_group_claim"),
        UniqueConstraint("processing_run_id", "claim_id", name="uq_story_claim_group_members_run_claim"),
        CheckConstraint(
            "similarity_score BETWEEN 0 AND 1",
            name="ck_story_claim_group_members_similarity",
        ),
        CheckConstraint(
            "match_kind IN ('exact', 'lexical')",
            name="ck_story_claim_group_members_match_kind",
        ),
    )

    group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_claim_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("article_claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("story_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(nullable=False)
    match_kind: Mapped[ClaimGroupMatchKind] = mapped_column(String(20), nullable=False)

    group: Mapped[StoryClaimGroup] = relationship(back_populates="members")
    claim: Mapped["ArticleClaim"] = relationship()
    processing_run: Mapped["StoryProcessingRun"] = relationship()


class StoryClaimRelation(BaseModel):
    __tablename__ = "story_claim_relations"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "left_group_id",
            "right_group_id",
            "relation_kind",
            name="uq_story_claim_relations_run_pair_kind",
        ),
        Index(
            "ix_story_claim_relations_active_story",
            "story_id",
            "relation_kind",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "left_group_id <> right_group_id",
            name="ck_story_claim_relations_distinct_groups",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_story_claim_relations_confidence"),
        CheckConstraint("relation_kind = 'contradicts'", name="ck_story_claim_relations_kind"),
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
    relation_kind: Mapped[ClaimRelationKind] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    analysis_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    processing_run: Mapped["StoryProcessingRun"] = relationship()
    left_group: Mapped[StoryClaimGroup] = relationship(foreign_keys=[left_group_id])
    right_group: Mapped[StoryClaimGroup] = relationship(foreign_keys=[right_group_id])
