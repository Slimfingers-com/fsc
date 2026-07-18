"""create feeds table

Revision ID: 8aba9497f0c3
Revises: ed6e86f99520
Create Date: 2026-07-18 19:26:10.396778

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8aba9497f0c3"
down_revision: Union[str, Sequence[str], None] = "ed6e86f99520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feeds",
        sa.Column(
            "source_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            server_default=sa.text("3"),
            nullable=False,
        ),
        sa.Column(
            "fetch_interval_minutes",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "last_fetched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_success_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "etag",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "last_modified",
            sa.Text(),
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
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "fetch_interval_minutes > 0",
            name="ck_feeds_fetch_interval_minutes_positive",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 4",
            name="ck_feeds_priority_range",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "name",
            name="uq_feeds_source_id_name",
        ),
        sa.UniqueConstraint(
            "url",
            name="uq_feeds_url",
        ),
    )

    op.create_index(
        op.f("ix_feeds_source_id"),
        "feeds",
        ["source_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO feeds (
            source_id,
            name,
            url,
            active,
            priority
        )
        SELECT
            id,
            'Main feed',
            rss_url,
            active,
            priority_tier
        FROM sources
        WHERE rss_url IS NOT NULL
          AND BTRIM(rss_url) <> ''
        """
    )

    op.drop_column(
        "sources",
        "rss_url",
    )


def downgrade() -> None:
    op.add_column(
        "sources",
        sa.Column(
            "rss_url",
            sa.Text(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE sources
        SET rss_url = selected_feed.url
        FROM (
            SELECT DISTINCT ON (source_id)
                source_id,
                url
            FROM feeds
            WHERE deleted_at IS NULL
            ORDER BY
                source_id,
                priority ASC,
                created_at ASC,
                id ASC
        ) AS selected_feed
        WHERE sources.id = selected_feed.source_id
        """
    )

    op.drop_index(
        op.f("ix_feeds_source_id"),
        table_name="feeds",
    )

    op.drop_table("feeds")
