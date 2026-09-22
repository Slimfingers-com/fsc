"""add party press outlet dimension

Revision ID: f6a9c2e7b1d4
Revises: a2d9e6b4c7f1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f6a9c2e7b1d4"
down_revision: str | None = "a2d9e6b4c7f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_outlets",
        sa.Column("party_press", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "source_outlets",
        sa.Column("party_affiliation", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_source_outlets_party_press", "source_outlets", ["party_press"])


def downgrade() -> None:
    op.drop_index("ix_source_outlets_party_press", table_name="source_outlets")
    op.drop_column("source_outlets", "party_affiliation")
    op.drop_column("source_outlets", "party_press")
