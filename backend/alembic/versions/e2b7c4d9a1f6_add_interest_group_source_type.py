"""add interest group source type

Revision ID: e2b7c4d9a1f6
Revises: a1c4e7f9b2d6
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e2b7c4d9a1f6"
down_revision: str | None = "a1c4e7f9b2d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PREVIOUS_SOURCE_TYPES = (
    "'NEWS', 'AGENCY', 'REGIONAL', 'ALTERNATIVE', 'PRIMARY_SOURCE', "
    "'NGO', 'COMPANY', 'ACADEMIC', 'THINK_TANK', 'SIGNAL'"
)


def upgrade() -> None:
    op.execute(
        "ALTER TYPE source_type "
        "ADD VALUE IF NOT EXISTS 'INTEREST_GROUP' AFTER 'NGO'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE sources "
        "ALTER COLUMN source_type TYPE text "
        "USING source_type::text"
    )
    op.execute("DROP TYPE source_type")
    op.execute(
        f"CREATE TYPE source_type AS ENUM ({_PREVIOUS_SOURCE_TYPES})"
    )
    op.execute(
        "ALTER TABLE sources "
        "ALTER COLUMN source_type TYPE source_type "
        "USING source_type::source_type"
    )
