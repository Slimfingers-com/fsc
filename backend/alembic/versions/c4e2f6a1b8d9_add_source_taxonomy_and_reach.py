"""add international source taxonomy and reach metadata

Revision ID: c4e2f6a1b8d9
Revises: b9d5f3a7c1e4
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4e2f6a1b8d9"
down_revision: str | None = "b9d5f3a7c1e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


media_family = postgresql.ENUM(
    "PRINT", "BROADCAST", "DIGITAL_NATIVE", "AGENCY",
    "PRIMARY_SOURCE", "ORGANIZATION", "ACADEMIC", "OTHER",
    name="media_family",
    create_type=False,
)

publication_format = postgresql.ENUM(
    "DAILY_NEWSPAPER", "WEEKLY_NEWSPAPER", "SUNDAY_NEWSPAPER",
    "MAGAZINE", "NEWS_MAGAZINE", "TRADE_MAGAZINE", "RADIO",
    "TELEVISION", "ONLINE_NEWS", "NEWS_AGENCY", "NEWSLETTER",
    "PODCAST", "OTHER",
    name="publication_format",
    create_type=False,
)

publication_frequency = postgresql.ENUM(
    "CONTINUOUS", "MULTIPLE_DAILY", "DAILY", "MULTIPLE_WEEKLY",
    "WEEKLY", "BIWEEKLY", "MONTHLY", "BIMONTHLY", "QUARTERLY",
    "SEMIANNUAL", "ANNUAL", "IRREGULAR", "OTHER",
    name="publication_frequency",
    create_type=False,
)

classification_kind = postgresql.ENUM(
    "POLITICAL_ORIENTATION", "RADICALITY",
    name="source_classification_kind",
    create_type=False,
)

reach_metric_type = postgresql.ENUM(
    "PRINT_SOLD_CIRCULATION", "PRINT_DISTRIBUTION",
    "EPAPER_CIRCULATION", "DIGITAL_UNIQUE_USERS", "DIGITAL_VISITS",
    "PAID_DIGITAL_SUBSCRIBERS", "SOCIAL_FOLLOWERS", "VIDEO_VIEWS",
    "OTHER",
    name="reach_metric_type",
    create_type=False,
)

reach_metric_quality = postgresql.ENUM(
    "AUDITED", "PUBLISHER_REPORTED", "THIRD_PARTY_ESTIMATE", "OTHER",
    name="reach_metric_quality",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    media_family.create(bind, checkfirst=True)
    publication_format.create(bind, checkfirst=True)
    publication_frequency.create(bind, checkfirst=True)
    classification_kind.create(bind, checkfirst=True)
    reach_metric_type.create(bind, checkfirst=True)
    reach_metric_quality.create(bind, checkfirst=True)

    op.add_column(
        "sources",
        sa.Column("media_family", media_family, nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("publication_format", publication_format, nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("publication_frequency", publication_frequency, nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column(
            "coverage_countries",
            postgresql.ARRAY(sa.String(length=2)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_index("ix_sources_media_family", "sources", ["media_family"])
    op.create_index(
        "ix_sources_publication_format",
        "sources",
        ["publication_format"],
    )
    op.create_index(
        "ix_sources_publication_frequency",
        "sources",
        ["publication_frequency"],
    )

    op.create_table(
        "source_classifications",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", classification_kind, nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("evidence_source_name", sa.String(length=255), nullable=False),
        sa.Column("evidence_url", sa.Text()),
        sa.Column("as_of", sa.Date()),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_classifications_active_source_kind",
        "source_classifications",
        ["source_id", "kind"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_source_classifications_active_primary_kind",
        "source_classifications",
        ["source_id", "kind"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND is_primary IS TRUE"),
    )

    op.create_table(
        "source_reach_metrics",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_type", reach_metric_type, nullable=False),
        sa.Column("metric_value", sa.BigInteger(), nullable=False),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("evidence_source_name", sa.String(length=255), nullable=False),
        sa.Column("evidence_url", sa.Text()),
        sa.Column(
            "quality",
            reach_metric_quality,
            server_default=sa.text("'OTHER'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "metric_value >= 0",
            name="ck_source_reach_metrics_value_nonnegative",
        ),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_source_reach_metrics_period_order",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_reach_metrics_active_source_type",
        "source_reach_metrics",
        ["source_id", "metric_type"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_reach_metrics_active_source_type",
        table_name="source_reach_metrics",
    )
    op.drop_table("source_reach_metrics")
    op.drop_index(
        "uq_source_classifications_active_primary_kind",
        table_name="source_classifications",
    )
    op.drop_index(
        "ix_source_classifications_active_source_kind",
        table_name="source_classifications",
    )
    op.drop_table("source_classifications")
    op.drop_index("ix_sources_publication_frequency", table_name="sources")
    op.drop_index("ix_sources_publication_format", table_name="sources")
    op.drop_index("ix_sources_media_family", table_name="sources")
    op.drop_column("sources", "coverage_countries")
    op.drop_column("sources", "publication_frequency")
    op.drop_column("sources", "publication_format")
    op.drop_column("sources", "media_family")

    bind = op.get_bind()
    reach_metric_quality.drop(bind, checkfirst=True)
    reach_metric_type.drop(bind, checkfirst=True)
    classification_kind.drop(bind, checkfirst=True)
    publication_frequency.drop(bind, checkfirst=True)
    publication_format.drop(bind, checkfirst=True)
    media_family.drop(bind, checkfirst=True)
