"""add feed worker claims

Revision ID: a6d48e7c912f
Revises: f5c83da2b704
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a6d48e7c912f"
down_revision: str | None = "f5c83da2b704"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feeds", sa.Column("claimed_at", sa.DateTime(timezone=True)))
    op.add_column("feeds", sa.Column("claimed_by", sa.String(100)))
    op.add_column("feeds", sa.Column("claim_expires_at", sa.DateTime(timezone=True)))
    op.create_index("ix_feeds_claimed_by", "feeds", ["claimed_by"])
    op.create_index("ix_feeds_claim_expires_at", "feeds", ["claim_expires_at"])
    op.create_index(
        "ix_feeds_worker_queue",
        "feeds",
        ["active", "claim_expires_at", "priority", "last_fetched_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_feeds_worker_queue", table_name="feeds")
    op.drop_index("ix_feeds_claim_expires_at", table_name="feeds")
    op.drop_index("ix_feeds_claimed_by", table_name="feeds")
    op.drop_column("feeds", "claim_expires_at")
    op.drop_column("feeds", "claimed_by")
    op.drop_column("feeds", "claimed_at")
