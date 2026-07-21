"""add article normalization fields

Revision ID: 7c61e2b493a4
Revises: 4f6b8a2d1c90
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "7c61e2b493a4"
down_revision: str | None = "4f6b8a2d1c90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("normalized_title", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("normalized_text", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("language_code", sa.String(length=16), nullable=True))
    op.add_column("articles", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("reading_time_minutes", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("articles", sa.Column("normalization_version", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_articles_language_code"), "articles", ["language_code"], unique=False)
    op.create_index(op.f("ix_articles_content_hash"), "articles", ["content_hash"], unique=False)
    op.create_index(op.f("ix_articles_normalized_at"), "articles", ["normalized_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_articles_normalized_at"), table_name="articles")
    op.drop_index(op.f("ix_articles_content_hash"), table_name="articles")
    op.drop_index(op.f("ix_articles_language_code"), table_name="articles")
    for column in (
        "normalized_at", "normalization_version", "content_hash",
        "reading_time_minutes", "word_count", "language_code",
        "normalized_text", "normalized_title",
    ):
        op.drop_column("articles", column)
