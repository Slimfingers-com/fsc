"""add processing run attempt uniqueness

Revision ID: f1c8d5a7b2e4
Revises: e9b4c7d2f3a5
"""
from collections.abc import Sequence

from alembic import op


revision: str = "f1c8d5a7b2e4"
down_revision: str | None = "e9b4c7d2f3a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_article_processing_runs_state_attempt",
        "article_processing_runs",
        [
            "processing_state_id",
            "attempt_number",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_article_processing_runs_state_attempt",
        table_name="article_processing_runs",
    )