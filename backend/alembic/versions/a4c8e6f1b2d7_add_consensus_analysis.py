"""add consensus and difference analysis

Revision ID: a4c8e6f1b2d7
Revises: f2a7c1d4e9b3
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a4c8e6f1b2d7"
down_revision: str | None = "f2a7c1d4e9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_consensus_summaries",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consensus_kind", sa.String(length=20), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("independent_source_count", sa.Integer(), nullable=False),
        sa.Column("evidence_item_count", sa.Integer(), nullable=False),
        sa.Column("evidence_source_count", sa.Integer(), nullable=False),
        sa.Column("attributed_perspective_count", sa.Integer(), nullable=False),
        sa.Column("analysis_provider", sa.String(length=100), nullable=False),
        sa.Column("analysis_version", sa.String(length=100), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["story_processing_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_group_id"], ["story_claim_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_group_id",
            name="uq_story_consensus_run_group",
        ),
        sa.CheckConstraint(
            "consensus_kind IN ('single_source', 'shared')",
            name="ck_story_consensus_kind",
        ),
        sa.CheckConstraint(
            "claim_count >= 1 AND article_count >= 1 "
            "AND independent_source_count >= 1 "
            "AND evidence_item_count >= 0 "
            "AND evidence_source_count >= 0 "
            "AND attributed_perspective_count >= 0",
            name="ck_story_consensus_counts",
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "claim_group_id",
        "consensus_kind",
    ):
        op.create_index(
            f"ix_story_consensus_summaries_{column}",
            "story_consensus_summaries",
            [column],
        )
    op.create_index(
        "uq_story_consensus_active_group",
        "story_consensus_summaries",
        ["story_id", "claim_group_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "story_difference_summaries",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_relation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("left_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("right_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("difference_kind", sa.String(length=20), nullable=False),
        sa.Column("left_independent_source_count", sa.Integer(), nullable=False),
        sa.Column("right_independent_source_count", sa.Integer(), nullable=False),
        sa.Column("left_evidence_source_count", sa.Integer(), nullable=False),
        sa.Column("right_evidence_source_count", sa.Integer(), nullable=False),
        sa.Column("analysis_provider", sa.String(length=100), nullable=False),
        sa.Column("analysis_version", sa.String(length=100), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["story_processing_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_relation_id"], ["story_claim_relations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["left_group_id"], ["story_claim_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["right_group_id"], ["story_claim_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_relation_id",
            name="uq_story_difference_run_relation",
        ),
        sa.CheckConstraint(
            "difference_kind = 'contradiction'",
            name="ck_story_difference_kind",
        ),
        sa.CheckConstraint(
            "left_group_id <> right_group_id",
            name="ck_story_difference_distinct_groups",
        ),
        sa.CheckConstraint(
            "left_independent_source_count >= 1 "
            "AND right_independent_source_count >= 1 "
            "AND left_evidence_source_count >= 0 "
            "AND right_evidence_source_count >= 0",
            name="ck_story_difference_counts",
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "claim_relation_id",
        "left_group_id",
        "right_group_id",
        "difference_kind",
    ):
        op.create_index(
            f"ix_story_difference_summaries_{column}",
            "story_difference_summaries",
            [column],
        )
    op.create_index(
        "uq_story_difference_active_relation",
        "story_difference_summaries",
        ["story_id", "claim_relation_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_story_difference_active_relation",
        table_name="story_difference_summaries",
    )
    for column in (
        "difference_kind",
        "right_group_id",
        "left_group_id",
        "claim_relation_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_difference_summaries_{column}",
            table_name="story_difference_summaries",
        )
    op.drop_table("story_difference_summaries")

    op.drop_index(
        "uq_story_consensus_active_group",
        table_name="story_consensus_summaries",
    )
    for column in (
        "consensus_kind",
        "claim_group_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_consensus_summaries_{column}",
            table_name="story_consensus_summaries",
        )
    op.drop_table("story_consensus_summaries")
