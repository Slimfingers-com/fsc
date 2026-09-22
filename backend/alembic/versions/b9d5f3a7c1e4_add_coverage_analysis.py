"""add coverage gaps and missing perspectives

Revision ID: b9d5f3a7c1e4
Revises: a4c8e6f1b2d7
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b9d5f3a7c1e4"
down_revision: str | None = "a4c8e6f1b2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_coverage_summaries",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consensus_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("content_source_count", sa.Integer(), nullable=False),
        sa.Column("signal_source_count", sa.Integer(), nullable=False),
        sa.Column("independent_content_owner_count", sa.Integer(), nullable=False),
        sa.Column("claim_group_count", sa.Integer(), nullable=False),
        sa.Column("shared_group_count", sa.Integer(), nullable=False),
        sa.Column("difference_count", sa.Integer(), nullable=False),
        sa.Column("attributed_group_count", sa.Integer(), nullable=False),
        sa.Column("source_type_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("coverage_scope_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("country_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["consensus_processing_run_id"], ["story_processing_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "story_id",
            name="uq_story_coverage_run_story",
        ),
        sa.CheckConstraint(
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
    for column in (
        "story_id",
        "processing_run_id",
        "consensus_processing_run_id",
    ):
        op.create_index(
            f"ix_story_coverage_summaries_{column}",
            "story_coverage_summaries",
            [column],
        )
    op.create_index(
        "uq_story_coverage_active_story",
        "story_coverage_summaries",
        ["story_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "story_coverage_gaps",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gap_key", sa.String(length=100), nullable=False),
        sa.Column("gap_kind", sa.String(length=50), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=False),
        sa.Column("minimum_expected", sa.Integer(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "gap_key",
            name="uq_story_coverage_gap_run_key",
        ),
        sa.CheckConstraint(
            "gap_kind IN ("
            "'limited_independent_content_sources', "
            "'signal_without_content_coverage')",
            name="ck_story_coverage_gap_kind",
        ),
        sa.CheckConstraint(
            "observed_count >= 0 "
            "AND (minimum_expected IS NULL OR minimum_expected >= 0)",
            name="ck_story_coverage_gap_counts",
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "gap_kind",
    ):
        op.create_index(
            f"ix_story_coverage_gaps_{column}",
            "story_coverage_gaps",
            [column],
        )
    op.create_index(
        "uq_story_coverage_gap_active_key",
        "story_coverage_gaps",
        ["story_id", "gap_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "story_missing_perspectives",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("missing_kind", sa.String(length=50), nullable=False),
        sa.Column(
            "contradiction_relation_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
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
            "missing_kind",
            name="uq_story_missing_perspective_run_group_kind",
        ),
        sa.CheckConstraint(
            "missing_kind = 'no_attributed_perspective'",
            name="ck_story_missing_perspective_kind",
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "claim_group_id",
        "missing_kind",
    ):
        op.create_index(
            f"ix_story_missing_perspectives_{column}",
            "story_missing_perspectives",
            [column],
        )
    op.create_index(
        "uq_story_missing_perspective_active_group_kind",
        "story_missing_perspectives",
        ["story_id", "claim_group_id", "missing_kind"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_story_missing_perspective_active_group_kind",
        table_name="story_missing_perspectives",
    )
    for column in (
        "missing_kind",
        "claim_group_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_missing_perspectives_{column}",
            table_name="story_missing_perspectives",
        )
    op.drop_table("story_missing_perspectives")

    op.drop_index(
        "uq_story_coverage_gap_active_key",
        table_name="story_coverage_gaps",
    )
    for column in (
        "gap_kind",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_coverage_gaps_{column}",
            table_name="story_coverage_gaps",
        )
    op.drop_table("story_coverage_gaps")

    op.drop_index(
        "uq_story_coverage_active_story",
        table_name="story_coverage_summaries",
    )
    for column in (
        "consensus_processing_run_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_coverage_summaries_{column}",
            table_name="story_coverage_summaries",
        )
    op.drop_table("story_coverage_summaries")
