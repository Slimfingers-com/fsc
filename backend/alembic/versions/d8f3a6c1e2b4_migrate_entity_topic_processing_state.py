"""migrate entity topic processing state

Revision ID: d8f3a6c1e2b4
Revises: c7a2f1e4b9d0
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8f3a6c1e2b4"
down_revision: str | None = "c7a2f1e4b9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "article_entities",
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_article_entities_processing_run_id",
        "article_entities",
        "article_processing_runs",
        ["processing_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_article_entities_processing_run_id",
        "article_entities",
        ["processing_run_id"],
    )

    op.add_column(
        "article_topics",
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_article_topics_processing_run_id",
        "article_topics",
        "article_processing_runs",
        ["processing_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_article_topics_processing_run_id",
        "article_topics",
        ["processing_run_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO article_processing_states (
                article_id,
                pipeline,
                processed_input_hash,
                processed_provider,
                processed_provider_version,
                processed_configuration_version,
                last_processed_at,
                attempt_count,
                retry_after,
                last_error_message,
                id,
                created_at,
                updated_at
            )
            SELECT
                a.id,
                'entity_topic',
                CASE
                    WHEN
                        a.entity_topic_analysis_hash IS NOT NULL
                        AND a.entity_topic_analysis_provider IS NOT NULL
                        AND a.entity_topic_analysis_version IS NOT NULL
                        AND a.entity_topic_analysis_config_version IS NOT NULL
                        AND a.entity_topic_analyzed_at IS NOT NULL
                    THEN a.entity_topic_analysis_hash
                    ELSE NULL
                END,
                CASE
                    WHEN
                        a.entity_topic_analysis_hash IS NOT NULL
                        AND a.entity_topic_analysis_provider IS NOT NULL
                        AND a.entity_topic_analysis_version IS NOT NULL
                        AND a.entity_topic_analysis_config_version IS NOT NULL
                        AND a.entity_topic_analyzed_at IS NOT NULL
                    THEN a.entity_topic_analysis_provider
                    ELSE NULL
                END,
                CASE
                    WHEN
                        a.entity_topic_analysis_hash IS NOT NULL
                        AND a.entity_topic_analysis_provider IS NOT NULL
                        AND a.entity_topic_analysis_version IS NOT NULL
                        AND a.entity_topic_analysis_config_version IS NOT NULL
                        AND a.entity_topic_analyzed_at IS NOT NULL
                    THEN a.entity_topic_analysis_version
                    ELSE NULL
                END,
                CASE
                    WHEN
                        a.entity_topic_analysis_hash IS NOT NULL
                        AND a.entity_topic_analysis_provider IS NOT NULL
                        AND a.entity_topic_analysis_version IS NOT NULL
                        AND a.entity_topic_analysis_config_version IS NOT NULL
                        AND a.entity_topic_analyzed_at IS NOT NULL
                    THEN a.entity_topic_analysis_config_version
                    ELSE NULL
                END,
                CASE
                    WHEN
                        a.entity_topic_analysis_hash IS NOT NULL
                        AND a.entity_topic_analysis_provider IS NOT NULL
                        AND a.entity_topic_analysis_version IS NOT NULL
                        AND a.entity_topic_analysis_config_version IS NOT NULL
                        AND a.entity_topic_analyzed_at IS NOT NULL
                    THEN a.entity_topic_analyzed_at
                    ELSE NULL
                END,
                GREATEST(a.entity_topic_attempt_count, 0),
                a.entity_topic_retry_after,
                a.entity_topic_analysis_error,
                gen_random_uuid(),
                now(),
                now()
            FROM articles AS a
            WHERE
                a.deleted_at IS NULL
                AND (
                    a.entity_topic_analysis_hash IS NOT NULL
                    OR a.entity_topic_analyzed_at IS NOT NULL
                    OR a.entity_topic_attempt_count > 0
                    OR a.entity_topic_retry_after IS NOT NULL
                    OR a.entity_topic_analysis_error IS NOT NULL
                    OR a.entity_topic_claimed_at IS NOT NULL
                    OR a.entity_topic_claimed_by IS NOT NULL
                    OR a.entity_topic_claim_expires_at IS NOT NULL
                )
            ON CONFLICT (article_id, pipeline)
                WHERE deleted_at IS NULL
            DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_article_topics_processing_run_id",
        table_name="article_topics",
    )
    op.drop_constraint(
        "fk_article_topics_processing_run_id",
        "article_topics",
        type_="foreignkey",
    )
    op.drop_column(
        "article_topics",
        "processing_run_id",
    )

    op.drop_index(
        "ix_article_entities_processing_run_id",
        table_name="article_entities",
    )
    op.drop_constraint(
        "fk_article_entities_processing_run_id",
        "article_entities",
        type_="foreignkey",
    )
    op.drop_column(
        "article_entities",
        "processing_run_id",
    )

    op.execute(
        sa.text(
            """
            DELETE FROM article_processing_states
            WHERE pipeline = 'entity_topic'
            """
        )
    )