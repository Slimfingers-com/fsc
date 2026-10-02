"""add disputed claim relations

Revision ID: e8c3f5a1b7d2
Revises: d7f2a4c8e1b5
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e8c3f5a1b7d2"
down_revision: str | None = "d7f2a4c8e1b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_story_claim_relations_kind",
        "story_claim_relations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_claim_relations_kind",
        "story_claim_relations",
        "relation_kind IN ('contradicts', 'disputes')",
    )

    op.drop_constraint(
        "ck_story_difference_kind",
        "story_difference_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_difference_kind",
        "story_difference_summaries",
        "difference_kind IN ('contradiction', 'dispute')",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM story_difference_summaries "
        "WHERE difference_kind = 'dispute'"
    )
    op.execute(
        "DELETE FROM story_claim_relations "
        "WHERE relation_kind = 'disputes'"
    )

    op.drop_constraint(
        "ck_story_difference_kind",
        "story_difference_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_difference_kind",
        "story_difference_summaries",
        "difference_kind = 'contradiction'",
    )

    op.drop_constraint(
        "ck_story_claim_relations_kind",
        "story_claim_relations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_claim_relations_kind",
        "story_claim_relations",
        "relation_kind = 'contradicts'",
    )
