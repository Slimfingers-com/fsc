"""add claim extraction

Revision ID: c2f8a1d4e7b9
Revises: b4e7c9d2a6f1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c2f8a1d4e7b9"
down_revision: str | None = "b4e7c9d2a6f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    text_part = postgresql.ENUM(
        "TITLE",
        "BODY",
        name="article_text_part",
        create_type=False,
    )

    op.create_table(
        "article_claims",
        sa.Column(
            "article_id",
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
            "claim_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "normalized_claim",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "claim_hash",
            sa.String(
                length=64
            ),
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
            "extraction_provider",
            sa.String(
                length=100
            ),
            nullable=False,
        ),
        sa.Column(
            "extraction_version",
            sa.String(
                length=100
            ),
            nullable=False,
        ),
        sa.Column(
            "extracted_at",
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
                "ck_article_claims_confidence"
            ),
        ),
        sa.CheckConstraint(
            "start_offset >= 0",
            name=(
                "ck_article_claims_start_offset"
            ),
        ),
        sa.CheckConstraint(
            "end_offset > start_offset",
            name=(
                "ck_article_claims_end_offset"
            ),
        ),
        sa.CheckConstraint(
            "sentence_index >= 0",
            name=(
                "ck_article_claims_sentence_index"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            [
                "article_processing_runs.id"
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "processing_run_id",
            "claim_hash",
            name=(
                "uq_article_claims_run_hash"
            ),
        ),
    )

    op.create_index(
        "ix_article_claims_article_id",
        "article_claims",
        ["article_id"],
    )
    op.create_index(
        "ix_article_claims_processing_run_id",
        "article_claims",
        ["processing_run_id"],
    )
    op.create_index(
        "ix_article_claims_claim_hash",
        "article_claims",
        ["claim_hash"],
    )
    op.create_index(
        "ix_article_claims_text_source",
        "article_claims",
        ["text_source"],
    )
    op.create_index(
        "uq_article_claims_active_article_hash",
        "article_claims",
        [
            "article_id",
            "claim_hash",
        ],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_article_claims_active_article_order",
        "article_claims",
        [
            "article_id",
            "text_source",
            "sentence_index",
            "start_offset",
        ],
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "article_claims"
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM "
            "article_processing_runs "
            "WHERE pipeline = "
            "'claim_extraction'"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM "
            "article_processing_states "
            "WHERE pipeline = "
            "'claim_extraction'"
        )
    )
