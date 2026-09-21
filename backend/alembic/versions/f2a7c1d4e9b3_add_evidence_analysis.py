"""add story evidence analysis

Revision ID: f2a7c1d4e9b3
Revises: e7b4d2c9a1f0
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2a7c1d4e9b3"
down_revision: str | None = "e7b4d2c9a1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_evidence",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evidence_kind",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "evidence_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "analysis_provider",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "analysis_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["story_processing_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["article_claims.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_id",
            name="uq_story_evidence_run_claim",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_story_evidence_confidence",
        ),
        sa.CheckConstraint(
            "evidence_kind IN ("
            "'primary_source', 'official_data', 'study', "
            "'direct_quote', 'press_release', "
            "'independent_reporting', 'context')",
            name="ck_story_evidence_kind",
        ),
    )

    for column in (
        "story_id",
        "processing_run_id",
        "claim_id",
        "article_id",
        "source_id",
        "evidence_kind",
    ):
        op.create_index(
            f"ix_story_evidence_{column}",
            "story_evidence",
            [column],
        )

    op.create_index(
        "uq_story_evidence_active_story_claim",
        "story_evidence",
        ["story_id", "claim_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "story_claim_evidence",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "claim_group_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "relation_kind",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
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
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["story_processing_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_group_id"],
            ["story_claim_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["story_evidence.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_group_id",
            "evidence_id",
            "relation_kind",
            name="uq_story_claim_evidence_run_group_evidence_kind",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="ck_story_claim_evidence_confidence",
        ),
        sa.CheckConstraint(
            "relation_kind IN ('supports', 'context')",
            name="ck_story_claim_evidence_relation_kind",
        ),
    )

    for column in (
        "story_id",
        "processing_run_id",
        "claim_group_id",
        "evidence_id",
        "relation_kind",
    ):
        op.create_index(
            f"ix_story_claim_evidence_{column}",
            "story_claim_evidence",
            [column],
        )

    op.create_index(
        "ix_story_claim_evidence_active_group",
        "story_claim_evidence",
        ["claim_group_id", "relation_kind"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_story_claim_evidence_active_group",
        table_name="story_claim_evidence",
    )
    for column in (
        "relation_kind",
        "evidence_id",
        "claim_group_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_claim_evidence_{column}",
            table_name="story_claim_evidence",
        )
    op.drop_table("story_claim_evidence")

    op.drop_index(
        "uq_story_evidence_active_story_claim",
        table_name="story_evidence",
    )
    for column in (
        "evidence_kind",
        "source_id",
        "article_id",
        "claim_id",
        "processing_run_id",
        "story_id",
    ):
        op.drop_index(
            f"ix_story_evidence_{column}",
            table_name="story_evidence",
        )
    op.drop_table("story_evidence")
