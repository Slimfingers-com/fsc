"""add semantic embeddings for multilingual analysis

Revision ID: c8f1a2d3e4b5
Revises: c3f8a6d2e1b4
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8f1a2d3e4b5"
down_revision: str | None = "c3f8a6d2e1b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_semantic_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "semantic_embedding",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
        ),
    )
    op.add_column(
        table_name,
        sa.Column(
            "semantic_model",
            sa.String(length=100),
            nullable=True,
        ),
    )


def upgrade() -> None:
    _add_semantic_columns("articles")
    op.add_column(
        "articles",
        sa.Column(
            "semantic_input_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "semantic_embedded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_articles_semantic_input_hash",
        "articles",
        ["semantic_input_hash"],
    )

    _add_semantic_columns("article_claims")
    op.add_column(
        "article_claims",
        sa.Column(
            "semantic_input_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "article_claims",
        sa.Column(
            "semantic_embedded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_article_claims_semantic_input_hash",
        "article_claims",
        ["semantic_input_hash"],
    )

    _add_semantic_columns("story_articles")

    op.drop_constraint(
        "ck_story_claim_group_members_match_kind",
        "story_claim_group_members",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_claim_group_members_match_kind",
        "story_claim_group_members",
        "match_kind IN ('exact', 'lexical', 'semantic')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_story_claim_group_members_match_kind",
        "story_claim_group_members",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_claim_group_members_match_kind",
        "story_claim_group_members",
        "match_kind IN ('exact', 'lexical')",
    )

    op.drop_column("story_articles", "semantic_model")
    op.drop_column("story_articles", "semantic_embedding")

    op.drop_index(
        "ix_article_claims_semantic_input_hash",
        table_name="article_claims",
    )
    op.drop_column("article_claims", "semantic_embedded_at")
    op.drop_column("article_claims", "semantic_input_hash")
    op.drop_column("article_claims", "semantic_model")
    op.drop_column("article_claims", "semantic_embedding")

    op.drop_index(
        "ix_articles_semantic_input_hash",
        table_name="articles",
    )
    op.drop_column("articles", "semantic_embedded_at")
    op.drop_column("articles", "semantic_input_hash")
    op.drop_column("articles", "semantic_model")
    op.drop_column("articles", "semantic_embedding")
