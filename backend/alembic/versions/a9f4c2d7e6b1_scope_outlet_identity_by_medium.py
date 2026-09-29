"""scope source outlet identity by medium

Revision ID: a9f4c2d7e6b1
Revises: f3d9a7c2e5b1
"""

from collections.abc import Sequence

from alembic import op


revision: str = "a9f4c2d7e6b1"
down_revision: str | None = "f3d9a7c2e5b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_CONSTRAINT = "uq_source_outlet_source_normalized_name"
_NEW_CONSTRAINT = (
    "uq_source_outlet_source_normalized_name_media_category"
)


def upgrade() -> None:
    op.drop_constraint(
        _OLD_CONSTRAINT,
        "source_outlets",
        type_="unique",
    )
    op.create_unique_constraint(
        _NEW_CONSTRAINT,
        "source_outlets",
        ["source_id", "normalized_name", "media_category"],
    )


def downgrade() -> None:
    op.drop_constraint(
        _NEW_CONSTRAINT,
        "source_outlets",
        type_="unique",
    )
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "source_outlets",
        ["source_id", "normalized_name"],
    )
