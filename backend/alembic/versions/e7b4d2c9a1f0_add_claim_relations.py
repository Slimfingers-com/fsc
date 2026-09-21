"""add story claim groups and relations

Revision ID: e7b4d2c9a1f0
Revises: d9a3c6e1f4b8
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7b4d2c9a1f0"
down_revision: str | None = "d9a3c6e1f4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "story_processing_states",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "pipeline",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "processed_input_hash",
            sa.String(length=64),
        ),
        sa.Column(
            "processed_provider",
            sa.String(length=100),
        ),
        sa.Column(
            "processed_provider_version",
            sa.String(length=100),
        ),
        sa.Column(
            "processed_configuration_version",
            sa.String(length=100),
        ),
        sa.Column(
            "last_processed_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "claimed_input_hash",
            sa.String(length=64),
        ),
        sa.Column(
            "claimed_provider",
            sa.String(length=100),
        ),
        sa.Column(
            "claimed_provider_version",
            sa.String(length=100),
        ),
        sa.Column(
            "claimed_configuration_version",
            sa.String(length=100),
        ),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "claimed_by",
            sa.String(length=100),
        ),
        sa.Column(
            "claim_expires_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "retry_after",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "last_started_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "last_error_code",
            sa.String(length=100),
        ),
        sa.Column(
            "last_error_message",
            sa.Text(),
        ),
        sa.Column(
            "last_error_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text(
                "gen_random_uuid()"
            ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=(
                "ck_story_processing_states_"
                "attempt_count_nonnegative"
            ),
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
            name=(
                "ck_story_processing_states_"
                "claim_complete"
            ),
        ),
        sa.CheckConstraint(
            "claim_expires_at IS NULL "
            "OR claim_expires_at > claimed_at",
            name=(
                "ck_story_processing_states_"
                "claim_expiry"
            ),
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
            name=(
                "ck_story_processing_states_"
                "processed_identity"
            ),
        ),
    )
    op.create_index(
        "uq_story_processing_states_active",
        "story_processing_states",
        ["story_id", "pipeline"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    for column in (
        "story_id",
        "pipeline",
        "last_processed_at",
        "claimed_by",
        "claim_expires_at",
        "retry_after",
    ):
        op.create_index(
            f"ix_story_processing_states_{column}",
            "story_processing_states",
            [column],
        )

    op.create_table(
        "story_processing_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text(
                "gen_random_uuid()"
            ),
            nullable=False,
        ),
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "processing_state_id",
            postgresql.UUID(as_uuid=True),
        ),
        sa.Column(
            "pipeline",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "input_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "provider_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "configuration_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "worker_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "outcome",
            sa.String(length=50),
        ),
        sa.Column(
            "error_code",
            sa.String(length=100),
        ),
        sa.Column(
            "error_message",
            sa.Text(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["processing_state_id"],
            ["story_processing_states.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "attempt_number > 0",
            name=(
                "ck_story_processing_runs_"
                "attempt_number_positive"
            ),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL "
            "OR finished_at >= started_at",
            name=(
                "ck_story_processing_runs_"
                "finished_after_started"
            ),
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('succeeded', 'failed', "
            "'skipped', 'lease_lost')",
            name=(
                "ck_story_processing_runs_"
                "outcome"
            ),
        ),
        sa.CheckConstraint(
            "(finished_at IS NULL "
            "AND outcome IS NULL) OR "
            "(finished_at IS NOT NULL "
            "AND outcome IS NOT NULL)",
            name=(
                "ck_story_processing_runs_"
                "completion_pair"
            ),
        ),
    )
    op.create_index(
        "uq_story_processing_runs_state_attempt",
        "story_processing_runs",
        [
            "processing_state_id",
            "attempt_number",
        ],
        unique=True,
    )
    for column in (
        "story_id",
        "processing_state_id",
        "pipeline",
        "worker_id",
        "outcome",
    ):
        op.create_index(
            f"ix_story_processing_runs_{column}",
            "story_processing_runs",
            [column],
        )

    op.create_table(
        "story_claim_groups",
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
            "representative_claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "group_hash",
            sa.String(length=64),
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
            server_default=sa.text(
                "gen_random_uuid()"
            ),
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
            ["representative_claim_id"],
            ["article_claims.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "group_hash",
            name=(
                "uq_story_claim_groups_"
                "run_hash"
            ),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name=(
                "ck_story_claim_groups_"
                "confidence"
            ),
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "representative_claim_id",
        "group_hash",
    ):
        op.create_index(
            f"ix_story_claim_groups_{column}",
            "story_claim_groups",
            [column],
        )
    op.create_index(
        "uq_story_claim_groups_active_story_hash",
        "story_claim_groups",
        ["story_id", "group_hash"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )

    op.create_table(
        "story_claim_group_members",
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "similarity_score",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "match_kind",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text(
                "gen_random_uuid()"
            ),
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
            ["group_id"],
            ["story_claim_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["article_claims.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["story_processing_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "claim_id",
            name=(
                "uq_story_claim_group_members_"
                "group_claim"
            ),
        ),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_id",
            name=(
                "uq_story_claim_group_members_"
                "run_claim"
            ),
        ),
        sa.CheckConstraint(
            "similarity_score BETWEEN 0 AND 1",
            name=(
                "ck_story_claim_group_members_"
                "similarity"
            ),
        ),
        sa.CheckConstraint(
            "match_kind IN ('exact', 'lexical')",
            name=(
                "ck_story_claim_group_members_"
                "match_kind"
            ),
        ),
    )
    for column in (
        "group_id",
        "claim_id",
        "processing_run_id",
    ):
        op.create_index(
            f"ix_story_claim_group_members_{column}",
            "story_claim_group_members",
            [column],
        )

    op.create_table(
        "story_claim_relations",
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
            "left_group_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "right_group_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "relation_kind",
            sa.String(length=30),
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
            server_default=sa.text(
                "gen_random_uuid()"
            ),
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
            ["left_group_id"],
            ["story_claim_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["right_group_id"],
            ["story_claim_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "processing_run_id",
            "left_group_id",
            "right_group_id",
            "relation_kind",
            name=(
                "uq_story_claim_relations_"
                "run_pair_kind"
            ),
        ),
        sa.CheckConstraint(
            "left_group_id <> right_group_id",
            name=(
                "ck_story_claim_relations_"
                "distinct_groups"
            ),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name=(
                "ck_story_claim_relations_"
                "confidence"
            ),
        ),
        sa.CheckConstraint(
            "relation_kind = 'contradicts'",
            name=(
                "ck_story_claim_relations_kind"
            ),
        ),
    )
    for column in (
        "story_id",
        "processing_run_id",
        "left_group_id",
        "right_group_id",
    ):
        op.create_index(
            f"ix_story_claim_relations_{column}",
            "story_claim_relations",
            [column],
        )
    op.create_index(
        "ix_story_claim_relations_active_story",
        "story_claim_relations",
        ["story_id", "relation_kind"],
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "story_claim_relations"
    )
    op.drop_table(
        "story_claim_group_members"
    )
    op.drop_table(
        "story_claim_groups"
    )
    op.drop_table(
        "story_processing_runs"
    )
    op.drop_table(
        "story_processing_states"
    )
