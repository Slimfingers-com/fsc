"""add perspective analysis

Revision ID: d9a3c6e1f4b8
Revises: c2f8a1d4e7b9
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d9a3c6e1f4b8"
down_revision: str | None = "c2f8a1d4e7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    perspective_kind_definition = postgresql.ENUM(
        "QUOTED",
        "REPORTED",
        "UNATTRIBUTED",
        name="perspective_kind",
    )
    perspective_kind_definition.create(
        bind,
        checkfirst=True,
    )

    perspective_kind = postgresql.ENUM(
        "QUOTED",
        "REPORTED",
        "UNATTRIBUTED",
        name="perspective_kind",
        create_type=False,
    )

    text_part = postgresql.ENUM(
        "TITLE",
        "BODY",
        name="article_text_part",
        create_type=False,
    )

    op.create_table(
        "article_perspectives",
        sa.Column(
            "article_id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=False,
        ),
        sa.Column(
            "holder_entity_id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=True,
        ),
        sa.Column(
            "holder_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "holder_start_offset",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "holder_end_offset",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "perspective_kind",
            perspective_kind,
            nullable=False,
        ),
        sa.Column(
            "evidence_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "text_source",
            text_part,
            nullable=False,
        ),
        sa.Column(
            "start_offset",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "end_offset",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sentence_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "analysis_provider",
            sa.String(
                length=100
            ),
            nullable=False,
        ),
        sa.Column(
            "analysis_version",
            sa.String(
                length=100
            ),
            nullable=False,
        ),
        sa.Column(
            "analyzed_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(
                as_uuid=True
            ),
            server_default=sa.text(
                "gen_random_uuid()"
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=True,
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name=(
                "ck_article_perspectives_confidence"
            ),
        ),
        sa.CheckConstraint(
            """
            (
                holder_start_offset IS NULL
                AND holder_end_offset IS NULL
            )
            OR
            (
                holder_start_offset IS NOT NULL
                AND holder_end_offset IS NOT NULL
                AND holder_start_offset >= 0
                AND holder_end_offset > holder_start_offset
            )
            """,
            name=(
                "ck_article_perspectives_holder_offsets"
            ),
        ),
        sa.CheckConstraint(
            "start_offset >= 0",
            name=(
                "ck_article_perspectives_start_offset"
            ),
        ),
        sa.CheckConstraint(
            "end_offset > start_offset",
            name=(
                "ck_article_perspectives_end_offset"
            ),
        ),
        sa.CheckConstraint(
            "sentence_index >= 0",
            name=(
                "ck_article_perspectives_sentence_index"
            ),
        ),
        sa.CheckConstraint(
            """
            (
                perspective_kind = 'UNATTRIBUTED'
                AND holder_entity_id IS NULL
                AND holder_text IS NULL
                AND holder_start_offset IS NULL
                AND holder_end_offset IS NULL
            )
            OR
            (
                perspective_kind IN ('QUOTED', 'REPORTED')
                AND holder_entity_id IS NOT NULL
                AND holder_text IS NOT NULL
                AND holder_start_offset IS NOT NULL
                AND holder_end_offset IS NOT NULL
            )
            """,
            name=(
                "ck_article_perspectives_holder_by_kind"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["article_claims.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            [
                "article_processing_runs.id"
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["holder_entity_id"],
            ["entities.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_id",
            "holder_entity_id",
            "perspective_kind",
            name=(
                "uq_article_perspectives_run_claim_holder_kind"
            ),
            postgresql_nulls_not_distinct=True,
        ),
    )

    op.create_index(
        "ix_article_perspectives_article_id",
        "article_perspectives",
        ["article_id"],
    )
    op.create_index(
        "ix_article_perspectives_claim_id",
        "article_perspectives",
        ["claim_id"],
    )
    op.create_index(
        "ix_article_perspectives_processing_run_id",
        "article_perspectives",
        ["processing_run_id"],
    )
    op.create_index(
        "ix_article_perspectives_holder_entity_id",
        "article_perspectives",
        ["holder_entity_id"],
    )
    op.create_index(
        "ix_article_perspectives_perspective_kind",
        "article_perspectives",
        ["perspective_kind"],
    )
    op.create_index(
        "ix_article_perspectives_text_source",
        "article_perspectives",
        ["text_source"],
    )
    op.create_index(
        "uq_article_perspectives_active_attributed",
        "article_perspectives",
        [
            "claim_id",
            "holder_entity_id",
            "perspective_kind",
        ],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL "
            "AND holder_entity_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_article_perspectives_active_unattributed",
        "article_perspectives",
        [
            "claim_id",
            "perspective_kind",
        ],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL "
            "AND holder_entity_id IS NULL"
        ),
    )
    op.create_index(
        "ix_article_perspectives_active_article_order",
        "article_perspectives",
        [
            "article_id",
            "claim_id",
            "perspective_kind",
        ],
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "article_perspectives"
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM "
            "article_processing_runs "
            "WHERE pipeline = "
            "'perspective_analysis'"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM "
            "article_processing_states "
            "WHERE pipeline = "
            "'perspective_analysis'"
        )
    )

    perspective_kind = postgresql.ENUM(
        "QUOTED",
        "REPORTED",
        "UNATTRIBUTED",
        name="perspective_kind",
    )
    perspective_kind.drop(
        connection,
        checkfirst=True,
    )
