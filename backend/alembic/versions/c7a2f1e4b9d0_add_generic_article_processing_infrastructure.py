"""add generic article processing infrastructure

Revision ID: c7a2f1e4b9d0
Revises: a6d48e7c912f
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7a2f1e4b9d0"
down_revision: str | None = "a6d48e7c912f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_processing_states",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline", sa.String(length=100), nullable=False),
        sa.Column("processed_input_hash", sa.String(length=64), nullable=True),
        sa.Column("processed_provider", sa.String(length=100), nullable=True),
        sa.Column("processed_provider_version", sa.String(length=100), nullable=True),
        sa.Column(
            "processed_configuration_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_input_hash", sa.String(length=64), nullable=True),
        sa.Column("claimed_provider", sa.String(length=100), nullable=True),
        sa.Column("claimed_provider_version", sa.String(length=100), nullable=True),
        sa.Column(
            "claimed_configuration_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(length=100), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_article_processing_states_attempt_count_nonnegative",
        ),
        sa.CheckConstraint(
            """
            (
                claimed_at IS NULL
                AND claimed_by IS NULL
                AND claim_expires_at IS NULL
                AND claimed_input_hash IS NULL
                AND claimed_provider IS NULL
                AND claimed_provider_version IS NULL
                AND claimed_configuration_version IS NULL
            )
            OR
            (
                claimed_at IS NOT NULL
                AND claimed_by IS NOT NULL
                AND claim_expires_at IS NOT NULL
                AND claimed_input_hash IS NOT NULL
                AND claimed_provider IS NOT NULL
                AND claimed_provider_version IS NOT NULL
                AND claimed_configuration_version IS NOT NULL
            )
            """,
            name="ck_article_processing_states_claim_complete",
        ),
        sa.CheckConstraint(
            "claim_expires_at IS NULL OR claim_expires_at > claimed_at",
            name="ck_article_processing_states_claim_expiry",
        ),
        sa.CheckConstraint(
            """
            (
                last_processed_at IS NULL
                AND processed_input_hash IS NULL
                AND processed_provider IS NULL
                AND processed_provider_version IS NULL
                AND processed_configuration_version IS NULL
            )
            OR
            (
                last_processed_at IS NOT NULL
                AND processed_input_hash IS NOT NULL
                AND processed_provider IS NOT NULL
                AND processed_provider_version IS NOT NULL
                AND processed_configuration_version IS NOT NULL
            )
            """,
            name="ck_article_processing_states_processed_identity",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_article_processing_states_article_id",
        "article_processing_states",
        ["article_id"],
    )
    op.create_index(
        "ix_article_processing_states_pipeline",
        "article_processing_states",
        ["pipeline"],
    )
    op.create_index(
        "ix_article_processing_states_last_processed_at",
        "article_processing_states",
        ["last_processed_at"],
    )
    op.create_index(
        "ix_article_processing_states_claimed_by",
        "article_processing_states",
        ["claimed_by"],
    )
    op.create_index(
        "ix_article_processing_states_claim_expires_at",
        "article_processing_states",
        ["claim_expires_at"],
    )
    op.create_index(
        "ix_article_processing_states_retry_after",
        "article_processing_states",
        ["retry_after"],
    )
    op.create_index(
        "uq_article_processing_states_active",
        "article_processing_states",
        ["article_id", "pipeline"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "article_processing_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "processing_state_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("pipeline", sa.String(length=100), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_version", sa.String(length=100), nullable=False),
        sa.Column(
            "configuration_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_number > 0",
            name="ck_article_processing_runs_attempt_number_positive",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_article_processing_runs_finished_after_started",
        ),
        sa.CheckConstraint(
            """
            outcome IS NULL
            OR outcome IN ('succeeded', 'failed', 'skipped', 'lease_lost')
            """,
            name="ck_article_processing_runs_outcome",
        ),
        sa.CheckConstraint(
            """
            (finished_at IS NULL AND outcome IS NULL)
            OR
            (finished_at IS NOT NULL AND outcome IS NOT NULL)
            """,
            name="ck_article_processing_runs_completion_pair",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["processing_state_id"],
            ["article_processing_states.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_article_processing_runs_article_id",
        "article_processing_runs",
        ["article_id"],
    )
    op.create_index(
        "ix_article_processing_runs_processing_state_id",
        "article_processing_runs",
        ["processing_state_id"],
    )
    op.create_index(
        "ix_article_processing_runs_pipeline",
        "article_processing_runs",
        ["pipeline"],
    )
    op.create_index(
        "ix_article_processing_runs_worker_id",
        "article_processing_runs",
        ["worker_id"],
    )
    op.create_index(
        "ix_article_processing_runs_outcome",
        "article_processing_runs",
        ["outcome"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_article_processing_runs_outcome",
        table_name="article_processing_runs",
    )
    op.drop_index(
        "ix_article_processing_runs_worker_id",
        table_name="article_processing_runs",
    )
    op.drop_index(
        "ix_article_processing_runs_pipeline",
        table_name="article_processing_runs",
    )
    op.drop_index(
        "ix_article_processing_runs_processing_state_id",
        table_name="article_processing_runs",
    )
    op.drop_index(
        "ix_article_processing_runs_article_id",
        table_name="article_processing_runs",
    )
    op.drop_table("article_processing_runs")

    op.drop_index(
        "uq_article_processing_states_active",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_retry_after",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_claim_expires_at",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_claimed_by",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_last_processed_at",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_pipeline",
        table_name="article_processing_states",
    )
    op.drop_index(
        "ix_article_processing_states_article_id",
        table_name="article_processing_states",
    )
    op.drop_table("article_processing_states")