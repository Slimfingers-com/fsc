"""add digital publication form

Revision ID: b1d7c4e8f2a6
Revises: a9f4c2d7e6b1
"""

from collections.abc import Sequence

from alembic import op


revision: str = "b1d7c4e8f2a6"
down_revision: str | None = "a9f4c2d7e6b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_source_outlet_publication_form"
_OLD = (
    "publication_form IN ("
    "'daily_newspaper', 'weekly_newspaper', 'sunday_newspaper', "
    "'magazine', 'periodical', 'radio', 'television', "
    "'digital_native', 'news_agency', 'other'"
    ")"
)
_NEW = (
    "publication_form IN ("
    "'daily_newspaper', 'weekly_newspaper', 'sunday_newspaper', "
    "'magazine', 'periodical', 'radio', 'television', "
    "'digital', 'digital_native', 'news_agency', 'other'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "source_outlets", type_="check")
    op.create_check_constraint(_CONSTRAINT, "source_outlets", _NEW)
def downgrade() -> None:
    op.execute(
        "UPDATE source_outlets "
        "SET publication_form = 'other' "
        "WHERE publication_form = 'digital'"
    )
    op.drop_constraint(_CONSTRAINT, "source_outlets", type_="check")
    op.create_check_constraint(_CONSTRAINT, "source_outlets", _OLD)
