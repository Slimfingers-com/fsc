"""add entity and topic detection

Revision ID: d3a91f52c8e0
Revises: b92f7d14c6a1
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d3a91f52c8e0"
down_revision: str | None = "b92f7d14c6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns():
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    entity_type = postgresql.ENUM("PERSON", "ORGANIZATION", "LOCATION", "EVENT", "PRODUCT", "OTHER", name="entity_type", create_type=False)
    entity_type.create(op.get_bind(), checkfirst=True)
    op.create_table("entities",
        sa.Column("canonical_name", sa.String(500), nullable=False), sa.Column("normalized_name", sa.String(500), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False), sa.Column("description", sa.Text()),
        sa.Column("external_ids", postgresql.JSONB()), sa.Column("aliases", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        *_base_columns(), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_entities_normalized_name", "entities", ["normalized_name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])
    op.create_index("ix_entities_aliases_gin", "entities", ["aliases"], postgresql_using="gin")
    op.create_index("uq_entities_active_name_type", "entities", ["normalized_name", "entity_type"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table("topics",
        sa.Column("name", sa.String(500), nullable=False), sa.Column("normalized_name", sa.String(500), nullable=False), sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("parent_topic_id", sa.UUID()), *_base_columns(),
        sa.ForeignKeyConstraint(["parent_topic_id"], ["topics.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_topics_normalized_name", "topics", ["normalized_name"])
    op.create_index("ix_topics_slug", "topics", ["slug"])
    op.create_index("ix_topics_parent_topic_id", "topics", ["parent_topic_id"])
    op.create_index("uq_topics_active_normalized_name", "topics", ["normalized_name"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_topics_active_slug", "topics", ["slug"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table("article_entities",
        sa.Column("article_id", sa.UUID(), nullable=False), sa.Column("entity_id", sa.UUID(), nullable=False), sa.Column("mention_text", sa.Text(), nullable=False),
        sa.Column("normalized_mention", sa.String(500), nullable=False), sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("start_offset", sa.Integer()), sa.Column("end_offset", sa.Integer()), sa.Column("sentence_index", sa.Integer()),
        sa.Column("confidence", sa.Float(), nullable=False), sa.Column("salience", sa.Float(), nullable=False),
        sa.Column("extraction_provider", sa.String(100), nullable=False), sa.Column("extraction_version", sa.String(100), nullable=False), *_base_columns(),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_article_entities_confidence"), sa.CheckConstraint("salience BETWEEN 0 AND 1", name="ck_article_entities_salience"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("article_id", "entity_id", "normalized_mention", "start_offset", "end_offset", name="uq_article_entity_mention", postgresql_nulls_not_distinct=True))
    for column in ("article_id", "entity_id", "normalized_mention", "entity_type"):
        op.create_index(f"ix_article_entities_{column}", "article_entities", [column])
    op.create_table("article_topics",
        sa.Column("article_id", sa.UUID(), nullable=False), sa.Column("topic_id", sa.UUID(), nullable=False), sa.Column("relevance", sa.Float(), nullable=False), sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detection_provider", sa.String(100), nullable=False), sa.Column("detection_version", sa.String(100), nullable=False), *_base_columns(),
        sa.CheckConstraint("relevance BETWEEN 0 AND 1", name="ck_article_topics_relevance"), sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_article_topics_confidence"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("article_id", "topic_id", name="uq_article_topics_article_topic"))
    op.create_index("ix_article_topics_article_id", "article_topics", ["article_id"])
    op.create_index("ix_article_topics_topic_id", "article_topics", ["topic_id"])
    op.add_column("articles", sa.Column("entity_topic_analysis_hash", sa.String(64)))
    op.add_column("articles", sa.Column("entity_topic_analysis_version", sa.String(100)))
    op.add_column("articles", sa.Column("entity_topic_analyzed_at", sa.DateTime(timezone=True)))
    op.add_column("articles", sa.Column("entity_topic_analysis_error", sa.Text()))
    op.create_index("ix_articles_entity_topic_analysis_hash", "articles", ["entity_topic_analysis_hash"])
    op.create_index("ix_articles_entity_topic_analyzed_at", "articles", ["entity_topic_analyzed_at"])


def downgrade() -> None:
    op.drop_index("ix_articles_entity_topic_analyzed_at", table_name="articles")
    op.drop_index("ix_articles_entity_topic_analysis_hash", table_name="articles")
    for column in ("entity_topic_analysis_error", "entity_topic_analyzed_at", "entity_topic_analysis_version", "entity_topic_analysis_hash"):
        op.drop_column("articles", column)
    op.drop_table("article_topics")
    op.drop_table("article_entities")
    op.drop_table("topics")
    op.drop_table("entities")
    postgresql.ENUM(name="entity_type").drop(op.get_bind(), checkfirst=True)
