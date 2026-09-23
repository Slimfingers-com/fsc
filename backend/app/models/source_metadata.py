from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.source_metadata import (
    PublicationForm,
    SourceClassificationDimension,
    SourceClassifierType,
    SourceMedium,
    SourceMetricKind,
)

if TYPE_CHECKING:
    from app.models.source import Source


class SourceOutlet(BaseModel):
    __tablename__ = "source_outlets"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "normalized_name",
            name="uq_source_outlet_source_normalized_name",
        ),
        CheckConstraint(
            "media_category IN ("
            "'print', 'broadcast', 'digital', 'agency', "
            "'primary_source', 'organization', 'other'"
            ")",
            name="ck_source_outlet_media_category",
        ),
        CheckConstraint(
            "publication_form IN ("
            "'daily_newspaper', 'weekly_newspaper', 'sunday_newspaper', "
            "'magazine', 'periodical', 'radio', 'television', "
            "'digital_native', 'news_agency', 'other'"
            ")",
            name="ck_source_outlet_publication_form",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_source_outlet_name_nonempty",
        ),
        Index(
            "ix_source_outlets_source_category_form",
            "source_id",
            "media_category",
            "publication_form",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    media_category: Mapped[SourceMedium] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    publication_form: Mapped[PublicationForm] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    publication_frequency: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    party_press: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    party_affiliation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    source: Mapped["Source"] = relationship(
        back_populates="outlets",
    )
    metrics: Mapped[list["SourceMetric"]] = relationship(
        back_populates="outlet",
    )


class SourceClassification(BaseModel):
    __tablename__ = "source_classifications"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "dimension",
            "value",
            "classifier_type",
            "classifier_name",
            "reference_date",
            name="uq_source_classification_assertion",
        ),
        CheckConstraint(
            "dimension IN ("
            "'editorial_orientation', 'radicality', "
            "'media_positioning', 'legal_status', 'other'"
            ")",
            name="ck_source_classification_dimension",
        ),
        CheckConstraint(
            "classifier_type IN ("
            "'self_description', 'media_database', 'academic', "
            "'public_authority', 'court', 'publisher', 'other'"
            ")",
            name="ck_source_classification_classifier_type",
        ),
        CheckConstraint(
            "btrim(value) <> ''",
            name="ck_source_classification_value_nonempty",
        ),
        CheckConstraint(
            "btrim(classifier_name) <> ''",
            name="ck_source_classification_classifier_nonempty",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_source_classification_valid_range",
        ),
        Index(
            "ix_source_classifications_source_dimension_reference",
            "source_id",
            "dimension",
            "reference_date",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension: Mapped[SourceClassificationDimension] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    classifier_type: Mapped[SourceClassifierType] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    classifier_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    reference_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    valid_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped["Source"] = relationship(
        back_populates="classifications",
    )


class SourceMetric(BaseModel):
    __tablename__ = "source_metrics"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "outlet_id",
            "metric_kind",
            "metric_scope",
            "reference_period",
            "measurement_body",
            "value",
            name="uq_source_metric_measurement",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "metric_kind IN ("
            "'sold_circulation', 'distributed_circulation', "
            "'print_run', 'print_readers', 'digital_unique_users', "
            "'visits', 'page_impressions', "
            "'paid_digital_subscriptions', 'subscribers', "
            "'radio_daily_listeners', 'radio_hourly_listeners', "
            "'radio_market_share', 'tv_viewers', 'tv_daily_reach', "
            "'tv_market_share'"
            ")",
            name="ck_source_metric_kind",
        ),
        CheckConstraint(
            "value >= 0",
            name="ck_source_metric_value_nonnegative",
        ),
        CheckConstraint(
            "btrim(metric_scope) <> ''",
            name="ck_source_metric_scope_nonempty",
        ),
        CheckConstraint(
            "btrim(unit) <> ''",
            name="ck_source_metric_unit_nonempty",
        ),
        CheckConstraint(
            "btrim(reference_period) <> ''",
            name="ck_source_metric_reference_period_nonempty",
        ),
        CheckConstraint(
            "btrim(measurement_body) <> ''",
            name="ck_source_metric_measurement_body_nonempty",
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL "
            "OR period_end >= period_start",
            name="ck_source_metric_period_range",
        ),
        Index(
            "ix_source_metrics_source_kind_period",
            "source_id",
            "metric_kind",
            "reference_period",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outlet_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("source_outlets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metric_kind: Mapped[SourceMetricKind] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="count",
    )
    metric_scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="source_total",
    )
    reference_period: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    period_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    period_end: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    measurement_body: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    audited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped["Source"] = relationship(
        back_populates="metrics",
    )
    outlet: Mapped[SourceOutlet | None] = relationship(
        back_populates="metrics",
    )
