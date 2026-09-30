"""replace provenance verified flag with review status

Revision ID: c6e1f4a9b2d7
Revises: b1d7c4e8f2a6
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c6e1f4a9b2d7"
down_revision: str | None = "b1d7c4e8f2a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "article_provenance",
        sa.Column(
            "review_status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )
    op.add_column(
        "article_provenance",
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE article_provenance "
        "SET review_status = CASE "
        "WHEN verified THEN 'verified' ELSE 'pending' END, "
        "reviewed_at = CASE WHEN verified THEN updated_at ELSE NULL END"
    )

    op.drop_index(
        "ix_article_provenance_article_verified",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_upstream_source_verified",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_verified",
        table_name="article_provenance",
    )
    op.drop_column("article_provenance", "verified")

    op.create_check_constraint(
        "ck_article_provenance_review_status",
        "article_provenance",
        "review_status IN ('pending', 'verified', 'rejected')",
    )
    op.create_index(
        "ix_article_provenance_review_status",
        "article_provenance",
        ["review_status"],
    )
    op.create_index(
        "ix_article_provenance_article_review_status",
        "article_provenance",
        ["article_id", "review_status"],
    )
    op.create_index(
        "ix_article_provenance_upstream_source_review_status",
        "article_provenance",
        ["upstream_source_id", "review_status"],
    )


def downgrade() -> None:
    op.add_column(
        "article_provenance",
        sa.Column(
            "verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE article_provenance "
        "SET verified = (review_status = 'verified')"
    )

    op.drop_index(
        "ix_article_provenance_upstream_source_review_status",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_article_review_status",
        table_name="article_provenance",
    )
    op.drop_index(
        "ix_article_provenance_review_status",
        table_name="article_provenance",
    )
    op.drop_constraint(
        "ck_article_provenance_review_status",
        "article_provenance",
        type_="check",
    )
    op.drop_column("article_provenance", "reviewed_at")
    op.drop_column("article_provenance", "review_status")

    op.create_index(
        "ix_article_provenance_verified",
        "article_provenance",
        ["verified"],
    )
    op.create_index(
        "ix_article_provenance_article_verified",
        "article_provenance",
        ["article_id", "verified"],
    )
    op.create_index(
        "ix_article_provenance_upstream_source_verified",
        "article_provenance",
        ["upstream_source_id", "verified"],
    )
