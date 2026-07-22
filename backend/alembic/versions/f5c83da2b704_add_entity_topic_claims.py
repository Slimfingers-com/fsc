"""add entity topic worker claims and retry state

Revision ID: f5c83da2b704
Revises: e4b72c91a6f3
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f5c83da2b704"
down_revision: str | None = "e4b72c91a6f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("article_entities", "text_part", new_column_name="text_source")
    op.execute("ALTER INDEX ix_article_entities_text_part RENAME TO ix_article_entities_text_source")
    op.add_column("articles", sa.Column("entity_topic_claimed_at", sa.DateTime(timezone=True)))
    op.add_column("articles", sa.Column("entity_topic_claimed_by", sa.String(100)))
    op.add_column("articles", sa.Column("entity_topic_claim_expires_at", sa.DateTime(timezone=True)))
    op.add_column("articles", sa.Column("entity_topic_attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("articles", sa.Column("entity_topic_retry_after", sa.DateTime(timezone=True)))
    op.create_index("ix_articles_entity_topic_claimed_by", "articles", ["entity_topic_claimed_by"])
    op.create_index("ix_articles_entity_topic_claim_expires_at", "articles", ["entity_topic_claim_expires_at"])
    op.create_index("ix_articles_entity_topic_retry_after", "articles", ["entity_topic_retry_after"])
    op.create_index("ix_articles_entity_topic_worker_queue", "articles", ["entity_topic_retry_after", "entity_topic_claim_expires_at", "created_at", "id"])
    op.drop_constraint("ck_article_entities_end_offset", "article_entities", type_="check")
    op.create_check_constraint("ck_article_entities_end_offset", "article_entities", "end_offset IS NULL OR end_offset > start_offset")


def downgrade() -> None:
    op.drop_constraint("ck_article_entities_end_offset", "article_entities", type_="check")
    op.create_check_constraint("ck_article_entities_end_offset", "article_entities", "end_offset IS NULL OR end_offset >= start_offset")
    op.drop_index("ix_articles_entity_topic_worker_queue", table_name="articles")
    op.drop_index("ix_articles_entity_topic_retry_after", table_name="articles")
    op.drop_index("ix_articles_entity_topic_claim_expires_at", table_name="articles")
    op.drop_index("ix_articles_entity_topic_claimed_by", table_name="articles")
    for column in ("entity_topic_retry_after", "entity_topic_attempt_count", "entity_topic_claim_expires_at", "entity_topic_claimed_by", "entity_topic_claimed_at"):
        op.drop_column("articles", column)
    op.execute("ALTER INDEX ix_article_entities_text_source RENAME TO ix_article_entities_text_part")
    op.alter_column("article_entities", "text_source", new_column_name="text_part")
