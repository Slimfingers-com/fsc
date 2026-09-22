"""add source subnational region

Revision ID: b7e3c1a9d5f2
Revises: f6a9c2e7b1d4
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3c1a9d5f2"
down_revision: str | None = "f6a9c2e7b1d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("subnational_region", sa.String(length=100), nullable=True))
    op.create_index("ix_sources_subnational_region", "sources", ["subnational_region"])


def downgrade() -> None:
    op.drop_index("ix_sources_subnational_region", table_name="sources")
    op.drop_column("sources", "subnational_region")
