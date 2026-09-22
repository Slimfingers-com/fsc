from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.enums.reach_metric_quality import ReachMetricQuality
from app.enums.reach_metric_type import ReachMetricType
from app.enums.source_classification import SourceClassificationKind

if TYPE_CHECKING:
    from app.models.source import Source


class SourceClassification(BaseModel):
    __tablename__ = "source_classifications"

    __table_args__ = (
        Index(
            "uq_source_classifications_active_primary_kind",
            "source_id",
            "kind",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND is_primary IS TRUE"
            ),
        ),
        Index(
            "ix_source_classifications_active_source_kind",
            "source_id",
            "kind",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[SourceClassificationKind] = mapped_column(
        Enum(
            SourceClassificationKind,
            name="source_classification_kind",
        ),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="classifications")


class SourceReachMetric(BaseModel):
    __tablename__ = "source_reach_metrics"

    __table_args__ = (
        CheckConstraint(
            "metric_value >= 0",
            name="ck_source_reach_metrics_value_nonnegative",
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL "
            "OR period_end >= period_start",
            name="ck_source_reach_metrics_period_order",
        ),
        Index(
            "ix_source_reach_metrics_active_source_type",
            "source_id",
            "metric_type",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_type: Mapped[ReachMetricType] = mapped_column(
        Enum(ReachMetricType, name="reach_metric_type"),
        nullable=False,
    )
    metric_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality: Mapped[ReachMetricQuality] = mapped_column(
        Enum(ReachMetricQuality, name="reach_metric_quality"),
        nullable=False,
        default=ReachMetricQuality.OTHER,
        server_default=text("'OTHER'"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="reach_metrics")
