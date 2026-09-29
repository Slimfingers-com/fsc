"""allow zero independent sources in consensus summaries

Revision ID: c6e2b8d4f1a9
Revises: f3d9a7c2e5b1
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c6e2b8d4f1a9"
down_revision: str | None = "f3d9a7c2e5b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_story_consensus_counts",
        "story_consensus_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_consensus_counts",
        "story_consensus_summaries",
        "claim_count >= 1 AND article_count >= 1 "
        "AND independent_source_count >= 0 "
        "AND evidence_item_count >= 0 "
        "AND evidence_source_count >= 0 "
        "AND attributed_perspective_count >= 0",
    )

    op.drop_constraint(
        "ck_story_difference_counts",
        "story_difference_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_difference_counts",
        "story_difference_summaries",
        "left_independent_source_count >= 0 "
        "AND right_independent_source_count >= 0 "
        "AND left_evidence_source_count >= 0 "
        "AND right_evidence_source_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_story_difference_counts",
        "story_difference_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_difference_counts",
        "story_difference_summaries",
        "left_independent_source_count >= 1 "
        "AND right_independent_source_count >= 1 "
        "AND left_evidence_source_count >= 0 "
        "AND right_evidence_source_count >= 0",
    )

    op.drop_constraint(
        "ck_story_consensus_counts",
        "story_consensus_summaries",
        type_="check",
    )
    op.create_check_constraint(
        "ck_story_consensus_counts",
        "story_consensus_summaries",
        "claim_count >= 1 AND article_count >= 1 "
        "AND independent_source_count >= 1 "
        "AND evidence_item_count >= 0 "
        "AND evidence_source_count >= 0 "
        "AND attributed_perspective_count >= 0",
    )
