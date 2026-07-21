"""fix entity and topic review issues

Revision ID: e4b72c91a6f3
Revises: d3a91f52c8e0
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e4b72c91a6f3"
down_revision: str | None = "d3a91f52c8e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    entity_type = postgresql.ENUM(name="entity_type", create_type=False)
    text_part = postgresql.ENUM("TITLE", "BODY", name="article_text_part", create_type=False)
    text_part.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "entity_aliases",
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("original_alias", sa.String(500), nullable=False),
        sa.Column("normalized_alias", sa.String(500), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_aliases_entity_id", "entity_aliases", ["entity_id"])
    op.create_index("ix_entity_aliases_entity_type", "entity_aliases", ["entity_type"])
    op.create_index("ix_entity_alias_lookup", "entity_aliases", ["normalized_alias", "entity_type"])
    op.create_index("uq_entity_aliases_active_entity_alias", "entity_aliases", ["entity_id", "normalized_alias"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.execute("""
        INSERT INTO entity_aliases (entity_id, original_alias, normalized_alias, entity_type)
        SELECT id, canonical_name, normalized_name, entity_type FROM entities
        UNION
        SELECT e.id, alias.value, lower(regexp_replace(trim(alias.value), '\\s+', ' ', 'g')), e.entity_type
        FROM entities e CROSS JOIN LATERAL jsonb_array_elements_text(e.aliases) AS alias(value)
        ON CONFLICT DO NOTHING
    """)
    op.drop_index("ix_entities_aliases_gin", table_name="entities")
    op.drop_column("entities", "aliases")

    op.add_column("article_entities", sa.Column("text_part", text_part, nullable=True))
    op.execute("""
        UPDATE article_entities ae SET
          text_part = CASE WHEN ae.start_offset IS NOT NULL AND ae.start_offset < length(coalesce(a.normalized_title, '')) THEN 'TITLE'::article_text_part ELSE 'BODY'::article_text_part END,
          start_offset = CASE WHEN ae.start_offset IS NOT NULL AND ae.start_offset >= length(coalesce(a.normalized_title, '')) + 1 THEN ae.start_offset - length(coalesce(a.normalized_title, '')) - 1 ELSE ae.start_offset END,
          end_offset = CASE WHEN ae.end_offset IS NOT NULL AND ae.start_offset >= length(coalesce(a.normalized_title, '')) + 1 THEN ae.end_offset - length(coalesce(a.normalized_title, '')) - 1 ELSE ae.end_offset END
        FROM articles a WHERE a.id = ae.article_id
    """)
    op.alter_column("article_entities", "text_part", nullable=False)
    op.drop_constraint("uq_article_entity_mention", "article_entities", type_="unique")
    op.create_unique_constraint("uq_article_entity_mention", "article_entities", ["article_id", "entity_id", "text_part", "normalized_mention", "start_offset", "end_offset"], postgresql_nulls_not_distinct=True)
    op.create_index("ix_article_entities_text_part", "article_entities", ["text_part"])
    op.create_check_constraint("ck_article_entities_start_offset", "article_entities", "start_offset IS NULL OR start_offset >= 0")
    op.create_check_constraint("ck_article_entities_end_offset", "article_entities", "end_offset IS NULL OR end_offset >= start_offset")
    op.create_check_constraint("ck_article_entities_offsets_pair", "article_entities", "(start_offset IS NULL) = (end_offset IS NULL)")
    op.create_check_constraint("ck_article_entities_sentence_index", "article_entities", "sentence_index IS NULL OR sentence_index >= 0")

    op.add_column("articles", sa.Column("entity_topic_analysis_provider", sa.String(100)))
    op.add_column("articles", sa.Column("entity_topic_analysis_config_version", sa.String(100)))
    op.add_column("articles", sa.Column("entity_topic_analysis_content_hash", sa.String(64)))
    op.add_column("articles", sa.Column("entity_topic_analysis_normalization_version", sa.Integer()))
    op.create_index("ix_articles_entity_topic_pending_identity", "articles", ["entity_topic_analysis_content_hash", "entity_topic_analysis_normalization_version", "entity_topic_analysis_provider", "entity_topic_analysis_version", "entity_topic_analysis_config_version"])


def downgrade() -> None:
    op.drop_index("ix_articles_entity_topic_pending_identity", table_name="articles")
    for column in ("entity_topic_analysis_normalization_version", "entity_topic_analysis_content_hash", "entity_topic_analysis_config_version", "entity_topic_analysis_provider"):
        op.drop_column("articles", column)
    for constraint in ("ck_article_entities_sentence_index", "ck_article_entities_offsets_pair", "ck_article_entities_end_offset", "ck_article_entities_start_offset"):
        op.drop_constraint(constraint, "article_entities", type_="check")
    op.drop_index("ix_article_entities_text_part", table_name="article_entities")
    op.drop_constraint("uq_article_entity_mention", "article_entities", type_="unique")
    op.create_unique_constraint("uq_article_entity_mention", "article_entities", ["article_id", "entity_id", "normalized_mention", "start_offset", "end_offset"], postgresql_nulls_not_distinct=True)
    op.drop_column("article_entities", "text_part")
    postgresql.ENUM(name="article_text_part").drop(op.get_bind(), checkfirst=True)
    op.add_column("entities", sa.Column("aliases", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.execute("""
        UPDATE entities e SET aliases = aliases.values
        FROM (SELECT entity_id, jsonb_agg(original_alias ORDER BY original_alias) AS values FROM entity_aliases WHERE normalized_alias <> (SELECT normalized_name FROM entities WHERE id = entity_id) GROUP BY entity_id) aliases
        WHERE e.id = aliases.entity_id
    """)
    op.create_index("ix_entities_aliases_gin", "entities", ["aliases"], postgresql_using="gin")
    op.drop_table("entity_aliases")
