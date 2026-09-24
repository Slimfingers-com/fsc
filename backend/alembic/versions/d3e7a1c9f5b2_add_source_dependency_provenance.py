"""add source dependency and article provenance

Revision ID: d3e7a1c9f5b2
Revises: b8d4e1f6a3c7
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d3e7a1c9f5b2"
down_revision: str | None = "b8d4e1f6a3c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_relations",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_kind", sa.String(length=40), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("provenance_url", sa.Text(), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source_id <> related_source_id",
            name="ck_source_relation_distinct_sources",
        ),
        sa.CheckConstraint(
            "relation_kind IN ("
            "'editorial_parent', 'shared_newsroom', 'content_supplier', "
            "'syndication_partner', 'joint_editorial_operation'"
            ")",
            name="ck_source_relation_kind",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_source_relation_valid_range",
        ),
    )
    op.create_index(
        "uq_source_relations_active_identity",
        "source_relations",
        [
            "source_id",
            "related_source_id",
            "relation_kind",
            "valid_from",
            "valid_to",
        ],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "ix_source_relations_source_id",
        "source_relations",
        ["source_id"],
    )
    op.create_index(
        "ix_source_relations_related_source_id",
        "source_relations",
        ["related_source_id"],
    )
    op.create_index(
        "ix_source_relations_relation_kind",
        "source_relations",
        ["relation_kind"],
    )
    op.create_index(
        "ix_source_relations_source_kind",
        "source_relations",
        ["source_id", "relation_kind"],
    )
    op.create_index(
        "ix_source_relations_related_kind",
        "source_relations",
        ["related_source_id", "relation_kind"],
    )

    op.create_table(
        "article_provenance",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upstream_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upstream_article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relation_kind", sa.String(length=40), nullable=False),
        sa.Column(
            "confidence",
            sa.Float(),
            server_default=sa.text("1.0"),
            nullable=False,
        ),
        sa.Column(
            "detection_method",
            sa.String(length=40),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column(
            "verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("provenance_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["upstream_source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["upstream_article_id"],
            ["articles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "upstream_article_id IS NULL OR article_id <> upstream_article_id",
            name="ck_article_provenance_distinct_articles",
        ),
        sa.CheckConstraint(
            "relation_kind IN ("
            "'supplied_by', 'syndicated_from', 'republished_from', "
            "'co_produced_with'"
            ")",
            name="ck_article_provenance_kind",
        ),
        sa.CheckConstraint(
            "detection_method IN ("
            "'manual', 'feed_metadata', 'provider_metadata', "
            "'canonical_url', 'byline', 'content_similarity', 'other'"
            ")",
            name="ck_article_provenance_detection_method",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_article_provenance_confidence_range",
        ),
    )
    op.create_index(
        "uq_article_provenance_active_identity",
        "article_provenance",
        [
            "article_id",
            "upstream_source_id",
            "upstream_article_id",
            "relation_kind",
        ],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "ix_article_provenance_article_id",
        "article_provenance",
        ["article_id"],
    )
    op.create_index(
        "ix_article_provenance_upstream_source_id",
        "article_provenance",
        ["upstream_source_id"],
    )
    op.create_index(
        "ix_article_provenance_upstream_article_id",
        "article_provenance",
        ["upstream_article_id"],
    )
    op.create_index(
        "ix_article_provenance_relation_kind",
        "article_provenance",
        ["relation_kind"],
    )
    op.create_index(
        "ix_article_provenance_detection_method",
        "article_provenance",
        ["detection_method"],
    )
    op.create_index(
        "ix_article_provenance_verified",
        "article_provenance",
        ["verified"],
    )
    op.create_index(
        "ix_article_provenance_article_verified",
        "article_provenance",
        ["article_id", "verified"],
    )
    op.create_index(
        "ix_article_provenance_upstream_source_verified",
        "article_provenance",
        ["upstream_source_id", "verified"],
    )

    op.drop_constraint(
        "ck_story_coverage_summary_counts",
        "story_coverage_summaries",
        type_="check",
    )
    op.alter_column(
        "story_coverage_summaries",
        "independent_content_owner_count",
        new_column_name="independent_content_source_count",
    )
    op.create_check_constraint(
        "ck_story_coverage_summary_counts",
        "story_coverage_summaries",
        "article_count >= 1 "
        "AND source_count >= 1 "
        "AND content_source_count >= 0 "
        "AND signal_source_count >= 0 "
        "AND independent_content_source_count >= 0 "
        "AND claim_group_count >= 1 "
        "AND shared_group_count >= 0 "
        "AND difference_count >= 0 "
        "AND attributed_group_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_story_coverage_summary_counts",
        "story_coverage_summaries",
        type_="check",
    )
    op.alter_column(
        "story_coverage_summaries",
        "independent_content_source_count",
        new_column_name="independent_content_owner_count",
    )
    op.create_check_constraint(
        "ck_story_coverage_summary_counts",
        "story_coverage_summaries",
        "article_count >= 1 "
        "AND source_count >= 1 "
        "AND content_source_count >= 0 "
        "AND signal_source_count >= 0 "
        "AND independent_content_owner_count >= 0 "
        "AND claim_group_count >= 1 "
        "AND shared_group_count >= 0 "
        "AND difference_count >= 0 "
        "AND attributed_group_count >= 0",
    )

    op.drop_index(
        "uq_article_provenance_active_identity",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_upstream_source_verified",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_article_verified",
        table_name="article_provenance",
    )
    op.drop_index("ix_article_provenance_verified", table_name="article_provenance")
    op.drop_index(
        "ix_article_provenance_detection_method",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_relation_kind",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_upstream_article_id",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_upstream_source_id",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_article_id",
        table_name="article_provenance",
    )
    op.drop_table("article_provenance")

    op.drop_index(
        "uq_source_relations_active_identity",
        table_name="source_relations",
    )
    op.drop_index(
        "ix_source_relations_related_kind",
        table_name="source_relations",
    )
    op.drop_index(
        "ix_source_relations_source_kind",
        table_name="source_relations",
    )
    op.drop_index(
        "ix_source_relations_relation_kind",
        table_name="source_relations",
    )
    op.drop_index(
        "ix_source_relations_related_source_id",
        table_name="source_relations",
    )
    op.drop_index(
        "ix_source_relations_source_id",
        table_name="source_relations",
    )
    op.drop_table("source_relations")
