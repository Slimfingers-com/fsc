"""add broadcast audience metric kinds

Revision ID: b8d4e1f6a3c7
Revises: b7e3c1a9d5f2
"""

from collections.abc import Sequence

from alembic import op


revision: str = "b8d4e1f6a3c7"
down_revision: str | None = "b7e3c1a9d5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_UPGRADED_KINDS = (
    "'sold_circulation', 'distributed_circulation', "
    "'print_run', 'print_readers', 'digital_unique_users', "
    "'visits', 'page_impressions', "
    "'paid_digital_subscriptions', 'subscribers', "
    "'radio_daily_listeners', 'radio_hourly_listeners', "
    "'radio_market_share', 'tv_viewers', 'tv_daily_reach', "
    "'tv_market_share'"
)

_PREVIOUS_KINDS = (
    "'sold_circulation', 'distributed_circulation', "
    "'print_run', 'print_readers', 'digital_unique_users', "
    "'visits', 'page_impressions', "
    "'paid_digital_subscriptions', 'subscribers'"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_source_metric_kind",
        "source_metrics",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_metric_kind",
        "source_metrics",
        f"metric_kind IN ({_UPGRADED_KINDS})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_source_metric_kind",
        "source_metrics",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_metric_kind",
        "source_metrics",
        f"metric_kind IN ({_PREVIOUS_KINDS})",
    )
