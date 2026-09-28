"""add feed default confirmation role

Revision ID: f3d9a7c2e5b1
Revises: e2b7c4d9a1f6
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3d9a7c2e5b1"
down_revision: str | None = "e2b7c4d9a1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ROLE_VALUES = (
    "'editorial', 'expert_analysis', 'primary_evidence', "
    "'advocacy', 'signal'"
)


def upgrade() -> None:
    op.add_column(
        "feeds",
        sa.Column(
            "default_confirmation_role",
            sa.String(length=32),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_feeds_default_confirmation_role",
        "feeds",
        f"default_confirmation_role IN ({_ROLE_VALUES})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_feeds_default_confirmation_role",
        "feeds",
        type_="check",
    )
    op.drop_column(
        "feeds",
        "default_confirmation_role",
    )
