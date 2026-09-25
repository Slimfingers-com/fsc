"""add article confirmation role

Revision ID: a1c4e7f9b2d6
Revises: d3e7a1c9f5b2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1c4e7f9b2d6"
down_revision: str | None = "d3e7a1c9f5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column(
            "confirmation_role",
            sa.String(length=32),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_articles_confirmation_role",
        "articles",
        (
            "confirmation_role IN ("
            "'editorial', 'expert_analysis', 'primary_evidence', "
            "'advocacy', 'signal'"
            ")"
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE articles AS a
            SET confirmation_role = CASE s.source_type::text
                WHEN 'PRIMARY_SOURCE' THEN 'primary_evidence'
                WHEN 'NGO' THEN 'advocacy'
                WHEN 'COMPANY' THEN 'advocacy'
                WHEN 'ACADEMIC' THEN 'expert_analysis'
                WHEN 'THINK_TANK' THEN 'expert_analysis'
                WHEN 'SIGNAL' THEN 'signal'
                ELSE 'editorial'
            END
            FROM feeds AS f
            JOIN sources AS s
              ON s.id = f.source_id
            WHERE a.feed_id = f.id
            """
        )
    )

    op.alter_column(
        "articles",
        "confirmation_role",
        existing_type=sa.String(length=32),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_articles_confirmation_role",
        "articles",
        type_="check",
    )
    op.drop_column(
        "articles",
        "confirmation_role",
    )
