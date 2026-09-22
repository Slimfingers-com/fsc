from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.enums.source_metadata import (
    SourceClassificationDimension,
    SourceClassifierType,
    SourceMetricKind,
)


class SourceClassificationCreate(BaseModel):
    dimension: SourceClassificationDimension
    value: str = Field(min_length=1, max_length=100)
    detail: str | None = None
    classifier_type: SourceClassifierType
    classifier_name: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    reference_date: date
    valid_from: date | None = None
    valid_to: date | None = None
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    notes: str | None = None

    @model_validator(mode="after")
    def validate_validity_range(self):
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("valid_to must not be before valid_from")
        return self


class SourceClassificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension: SourceClassificationDimension
    value: str
    detail: str | None
    classifier_type: SourceClassifierType
    classifier_name: str
    source_url: str
    reference_date: date
    valid_from: date | None
    valid_to: date | None
    retrieved_at: datetime
    notes: str | None


class SourceMetricCreate(BaseModel):
    metric_kind: SourceMetricKind
    value: int = Field(ge=0)
    unit: str = Field(default="count", min_length=1, max_length=50)
    metric_scope: str = Field(
        default="source_total",
        min_length=1,
        max_length=255,
    )
    reference_period: str = Field(min_length=1, max_length=100)
    period_start: date | None = None
    period_end: date | None = None
    measurement_body: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    audited: bool = False
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    notes: str | None = None

    @model_validator(mode="after")
    def validate_period_range(self):
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end must not be before period_start")
        return self


class SourceMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_kind: SourceMetricKind
    value: int
    unit: str
    metric_scope: str
    reference_period: str
    period_start: date | None
    period_end: date | None
    measurement_body: str
    source_url: str
    audited: bool
    retrieved_at: datetime
    notes: str | None
