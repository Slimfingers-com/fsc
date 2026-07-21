"""create articles table

Revision ID: 4f6b8a2d1c90
Revises: 8aba9497f0c3
Create Date: 2026-07-21 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f6b8a2d1c90"
down_revision: Union[str, Sequence[str], None] = "8aba9497f0c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


article_identity_type = sa.Enum(
    "GUID",
    "LINK",
    "DERIVED",
    name="article_identity_type",
)


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("feed_id", sa.UUID(), nullable=False),
        sa.Column(
            "identity_type",
            article_identity_type,
            nullable=False,
        ),
        sa.Column("identity_key", sa.String(length=64), nullable=False),
        sa.Column("guid", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "source_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["feeds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "feed_id",
            "identity_key",
            name="uq_articles_feed_id_identity_key",
        ),
    )

    op.create_index(
        op.f("ix_articles_feed_id"),
        "articles",
        ["feed_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_articles_published_at"),
        "articles",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_articles_published_at"), table_name="articles")
    op.drop_index(op.f("ix_articles_feed_id"), table_name="articles")
    op.drop_table("articles")
    article_identity_type.drop(op.get_bind(), checkfirst=True)
