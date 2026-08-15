"""remove legacy entity topic article state

Revision ID: e9b4c7d2f3a5
Revises: d8f3a6c1e2b4
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e9b4c7d2f3a5"
down_revision: str | None = "d8f3a6c1e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column(
        "articles",
        "entity_topic_analysis_hash",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_version",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_provider",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_config_version",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_content_hash",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_normalization_version",
    )
    op.drop_column(
        "articles",
        "entity_topic_claimed_at",
    )
    op.drop_column(
        "articles",
        "entity_topic_claimed_by",
    )
    op.drop_column(
        "articles",
        "entity_topic_claim_expires_at",
    )
    op.drop_column(
        "articles",
        "entity_topic_attempt_count",
    )
    op.drop_column(
        "articles",
        "entity_topic_retry_after",
    )
    op.drop_column(
        "articles",
        "entity_topic_analyzed_at",
    )
    op.drop_column(
        "articles",
        "entity_topic_analysis_error",
    )


def downgrade() -> None:
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_version",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_provider",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_config_version",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_content_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_normalization_version",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_claimed_by",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_claim_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_retry_after",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analyzed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "entity_topic_analysis_error",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_articles_entity_topic_analysis_hash",
        "articles",
        ["entity_topic_analysis_hash"],
    )
    op.create_index(
        "ix_articles_entity_topic_analyzed_at",
        "articles",
        ["entity_topic_analyzed_at"],
    )
    op.create_index(
        "ix_articles_entity_topic_claimed_by",
        "articles",
        ["entity_topic_claimed_by"],
    )
    op.create_index(
        "ix_articles_entity_topic_claim_expires_at",
        "articles",
        ["entity_topic_claim_expires_at"],
    )
    op.create_index(
        "ix_articles_entity_topic_retry_after",
        "articles",
        ["entity_topic_retry_after"],
    )
    op.create_index(
        "ix_articles_entity_topic_pending_identity",
        "articles",
        [
            "entity_topic_analysis_content_hash",
            "entity_topic_analysis_normalization_version",
            "entity_topic_analysis_provider",
            "entity_topic_analysis_version",
            "entity_topic_analysis_config_version",
        ],
    )
    op.create_index(
        "ix_articles_entity_topic_worker_queue",
        "articles",
        [
            "entity_topic_retry_after",
            "entity_topic_claim_expires_at",
            "created_at",
            "id",
        ],
    )