"""add story clustering

Revision ID: b4e7c9d2a6f1
Revises: a2d9e6b4c7f1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b4e7c9d2a6f1"
down_revision: str | None = "a2d9e6b4c7f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column(
            "language_code",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_stories_active_language",
        "stories",
        ["language_code"],
        unique=False,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )

    op.create_table(
        "story_articles",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "article_title",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "article_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "title_terms",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text(
                "'{}'::text[]"
            ),
            nullable=False,
        ),
        sa.Column(
            "entity_ids",
            postgresql.ARRAY(
                postgresql.UUID(as_uuid=True)
            ),
            server_default=sa.text(
                "'{}'::uuid[]"
            ),
            nullable=False,
        ),
        sa.Column(
            "topic_ids",
            postgresql.ARRAY(
                postgresql.UUID(as_uuid=True)
            ),
            server_default=sa.text(
                "'{}'::uuid[]"
            ),
            nullable=False,
        ),
        sa.Column(
            "similarity_score",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "match_kind",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "match_details",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "clustered_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "similarity_score BETWEEN 0 AND 1",
            name="ck_story_articles_similarity_score",
        ),
        sa.CheckConstraint(
            "match_kind IN ('created', 'matched', 'retained')",
            name="ck_story_articles_match_kind",
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["article_processing_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_story_articles_story_id",
        "story_articles",
        ["story_id"],
        unique=False,
    )
    op.create_index(
        "ix_story_articles_article_id",
        "story_articles",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        "uq_story_articles_active_article",
        "story_articles",
        ["article_id"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "uq_story_articles_processing_run",
        "story_articles",
        ["processing_run_id"],
        unique=True,
    )
    op.create_index(
        "ix_story_articles_active_story_time",
        "story_articles",
        ["story_id", "article_time"],
        unique=False,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_story_articles_active_time",
        "story_articles",
        ["article_time"],
        unique=False,
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_story_articles_active_title_terms_gin",
        "story_articles",
        ["title_terms"],
        unique=False,
        postgresql_using="gin",
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_story_articles_active_entity_ids_gin",
        "story_articles",
        ["entity_ids"],
        unique=False,
        postgresql_using="gin",
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_story_articles_active_topic_ids_gin",
        "story_articles",
        ["topic_ids"],
        unique=False,
        postgresql_using="gin",
        postgresql_where=sa.text(
            "deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table("story_articles")
    op.drop_table("stories")
