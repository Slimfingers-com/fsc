"""create search documents table

Revision ID: b92f7d14c6a1
Revises: 7c61e2b493a4
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b92f7d14c6a1"
down_revision: str | None = "7c61e2b493a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_documents",
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("builder_version", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple'::regconfig, coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('simple'::regconfig, coalesce(body, '')), 'B')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", name="uq_search_documents_article_id"),
    )
    op.create_index("ix_search_documents_source_id", "search_documents", ["source_id"])
    op.create_index("ix_search_documents_source_slug", "search_documents", ["source_slug"])
    op.create_index("ix_search_documents_language_code", "search_documents", ["language_code"])
    op.create_index("ix_search_documents_published_at", "search_documents", ["published_at"])
    op.create_index("ix_search_documents_search_vector", "search_documents", ["search_vector"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("search_documents")
