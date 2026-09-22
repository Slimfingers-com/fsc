"""add source catalog metadata

Revision ID: c3f8a6d2e1b4
Revises: b9d5f3a7c1e4
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3f8a6d2e1b4"
down_revision: str | None = "b9d5f3a7c1e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_outlets",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("media_category", sa.String(length=30), nullable=False),
        sa.Column("publication_form", sa.String(length=40), nullable=False),
        sa.Column("publication_frequency", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "name",
            name="uq_source_outlet_source_name",
        ),
        sa.CheckConstraint(
            "media_category IN ("
            "'print', 'broadcast', 'digital', 'agency', "
            "'primary_source', 'organization', 'other'"
            ")",
            name="ck_source_outlet_media_category",
        ),
        sa.CheckConstraint(
            "publication_form IN ("
            "'daily_newspaper', 'weekly_newspaper', 'sunday_newspaper', "
            "'magazine', 'periodical', 'radio', 'television', "
            "'digital_native', 'news_agency', 'other'"
            ")",
            name="ck_source_outlet_publication_form",
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_source_outlet_name_nonempty",
        ),
    )
    op.create_index(
        "ix_source_outlets_source_id",
        "source_outlets",
        ["source_id"],
    )
    op.create_index(
        "ix_source_outlets_media_category",
        "source_outlets",
        ["media_category"],
    )
    op.create_index(
        "ix_source_outlets_publication_form",
        "source_outlets",
        ["publication_form"],
    )
    op.create_index(
        "ix_source_outlets_source_category_form",
        "source_outlets",
        ["source_id", "media_category", "publication_form"],
    )

    op.create_table(
        "source_classifications",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("classifier_type", sa.String(length=40), nullable=False),
        sa.Column("classifier_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "dimension",
            "value",
            "classifier_type",
            "classifier_name",
            "reference_date",
            name="uq_source_classification_assertion",
        ),
        sa.CheckConstraint(
            "dimension IN ("
            "'editorial_orientation', 'radicality', "
            "'media_positioning', 'legal_status', 'other'"
            ")",
            name="ck_source_classification_dimension",
        ),
        sa.CheckConstraint(
            "classifier_type IN ("
            "'self_description', 'media_database', 'academic', "
            "'public_authority', 'court', 'publisher', 'other'"
            ")",
            name="ck_source_classification_classifier_type",
        ),
        sa.CheckConstraint(
            "btrim(value) <> ''",
            name="ck_source_classification_value_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(classifier_name) <> ''",
            name="ck_source_classification_classifier_nonempty",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_source_classification_valid_range",
        ),
    )
    op.create_index(
        "ix_source_classifications_source_id",
        "source_classifications",
        ["source_id"],
    )
    op.create_index(
        "ix_source_classifications_dimension",
        "source_classifications",
        ["dimension"],
    )
    op.create_index(
        "ix_source_classifications_classifier_type",
        "source_classifications",
        ["classifier_type"],
    )
    op.create_index(
        "ix_source_classifications_reference_date",
        "source_classifications",
        ["reference_date"],
    )
    op.create_index(
        "ix_source_classifications_source_dimension_reference",
        "source_classifications",
        ["source_id", "dimension", "reference_date"],
    )

    op.create_table(
        "source_metrics",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outlet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_kind", sa.String(length=50), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("metric_scope", sa.String(length=255), nullable=False),
        sa.Column("reference_period", sa.String(length=100), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("measurement_body", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "audited",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["outlet_id"],
            ["source_outlets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "metric_kind",
            "metric_scope",
            "reference_period",
            "measurement_body",
            "value",
            name="uq_source_metric_measurement",
        ),
        sa.CheckConstraint(
            "metric_kind IN ("
            "'sold_circulation', 'distributed_circulation', "
            "'print_run', 'print_readers', 'digital_unique_users', "
            "'visits', 'page_impressions', "
            "'paid_digital_subscriptions', 'subscribers'"
            ")",
            name="ck_source_metric_kind",
        ),
        sa.CheckConstraint(
            "value >= 0",
            name="ck_source_metric_value_nonnegative",
        ),
        sa.CheckConstraint(
            "btrim(metric_scope) <> ''",
            name="ck_source_metric_scope_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(unit) <> ''",
            name="ck_source_metric_unit_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(reference_period) <> ''",
            name="ck_source_metric_reference_period_nonempty",
        ),
        sa.CheckConstraint(
            "btrim(measurement_body) <> ''",
            name="ck_source_metric_measurement_body_nonempty",
        ),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL "
            "OR period_end >= period_start",
            name="ck_source_metric_period_range",
        ),
    )
    op.create_index(
        "ix_source_metrics_source_id",
        "source_metrics",
        ["source_id"],
    )
    op.create_index(
        "ix_source_metrics_outlet_id",
        "source_metrics",
        ["outlet_id"],
    )
    op.create_index(
        "ix_source_metrics_metric_kind",
        "source_metrics",
        ["metric_kind"],
    )
    op.create_index(
        "ix_source_metrics_source_kind_period",
        "source_metrics",
        ["source_id", "metric_kind", "reference_period"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_metrics_source_kind_period",
        table_name="source_metrics",
    )
    op.drop_index("ix_source_metrics_metric_kind", table_name="source_metrics")
    op.drop_index("ix_source_metrics_outlet_id", table_name="source_metrics")
    op.drop_index("ix_source_metrics_source_id", table_name="source_metrics")
    op.drop_table("source_metrics")

    op.drop_index(
        "ix_source_classifications_source_dimension_reference",
        table_name="source_classifications",
    )
    op.drop_index(
        "ix_source_classifications_reference_date",
        table_name="source_classifications",
    )
    op.drop_index(
        "ix_source_classifications_classifier_type",
        table_name="source_classifications",
    )
    op.drop_index(
        "ix_source_classifications_dimension",
        table_name="source_classifications",
    )
    op.drop_index(
        "ix_source_classifications_source_id",
        table_name="source_classifications",
    )
    op.drop_table("source_classifications")

    op.drop_index(
        "ix_source_outlets_source_category_form",
        table_name="source_outlets",
    )
    op.drop_index(
        "ix_source_outlets_publication_form",
        table_name="source_outlets",
    )
    op.drop_index(
        "ix_source_outlets_media_category",
        table_name="source_outlets",
    )
    op.drop_index("ix_source_outlets_source_id", table_name="source_outlets")
    op.drop_table("source_outlets")
