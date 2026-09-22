from datetime import date
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.enums.coverage_scope import CoverageScope
from app.enums.media_family import MediaFamily
from app.enums.publication_format import PublicationFormat
from app.enums.reach_metric_type import ReachMetricType
from app.enums.source_classification import (
    PoliticalOrientation,
    SourceClassificationKind,
    SourceRadicality,
)
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate, FeedRead


class SourceClassificationCreate(BaseModel):
    kind: SourceClassificationKind
    value: str = Field(min_length=1, max_length=100)
    detail: str | None = None
    evidence_source_name: str = Field(min_length=1, max_length=255)
    evidence_url: HttpUrl | None = None
    as_of: date | None = None
    is_primary: bool = True
    notes: str | None = None

    @model_validator(mode="after")
    def validate_value(self):
        if self.kind == SourceClassificationKind.POLITICAL_ORIENTATION:
            PoliticalOrientation(self.value)
        elif self.kind == SourceClassificationKind.RADICALITY:
            SourceRadicality(self.value)
        return self


class SourceClassificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: SourceClassificationKind
    value: str
    detail: str | None
    evidence_source_name: str
    evidence_url: str | None
    as_of: date | None
    is_primary: bool
    notes: str | None


class SourceReachMetricCreate(BaseModel):
    metric_type: ReachMetricType
    metric_value: int = Field(ge=0)
    period_start: date | None = None
    period_end: date | None = None
    evidence_source_name: str = Field(min_length=1, max_length=255)
    evidence_url: HttpUrl | None = None
    audited: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end must not be before period_start")
        return self


class SourceReachMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_type: ReachMetricType
    metric_value: int
    period_start: date | None
    period_end: date | None
    evidence_source_name: str
    evidence_url: str | None
    audited: bool
    notes: str | None


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

    url: HttpUrl
    api_url: HttpUrl | None = None

    source_type: SourceType
    coverage_scope: CoverageScope | None = None

    country: str | None = Field(default=None, min_length=2, max_length=2)
    language: str | None = Field(default=None, min_length=2, max_length=10)
    media_family: MediaFamily | None = None
    publication_format: PublicationFormat | None = None
    coverage_countries: list[str] = Field(default_factory=list)

    ownership: str | None = None
    funding_model: str | None = Field(default=None, max_length=100)

    paywall: bool = False
    transparency_level: int | None = Field(default=None, ge=0, le=100)
    correction_policy: str | None = None
    primary_source_usage: int | None = Field(default=None, ge=0, le=100)
    priority_tier: int = Field(default=3, ge=1, le=4)

    classifications: list[SourceClassificationCreate] = Field(
        default_factory=list
    )
    reach_metrics: list[SourceReachMetricCreate] = Field(default_factory=list)
    feeds: list[FeedCreate] = Field(default_factory=list)

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("coverage_countries")
    @classmethod
    def normalize_coverage_countries(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            country = value.strip().upper()
            if len(country) != 2 or not country.isalpha():
                raise ValueError(
                    "coverage country codes must contain exactly two letters"
                )
            if country not in seen:
                normalized.append(country)
                seen.add(country)
        return normalized

    @model_validator(mode="after")
    def validate_primary_classifications(self):
        primary_kinds: set[SourceClassificationKind] = set()
        for classification in self.classifications:
            if not classification.is_primary:
                continue
            if classification.kind in primary_kinds:
                raise ValueError(
                    "only one primary classification per kind is allowed"
                )
            primary_kinds.add(classification.kind)
        return self


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    normalized_name: str

    description: str | None

    url: str
    api_url: str | None

    source_type: SourceType
    coverage_scope: CoverageScope | None

    country: str | None
    language: str | None
    media_family: MediaFamily | None
    publication_format: PublicationFormat | None
    coverage_countries: list[str]

    ownership: str | None
    funding_model: str | None

    paywall: bool
    active: bool

    transparency_level: int | None
    correction_policy: str | None
    primary_source_usage: int | None
    priority_tier: int

    classifications: list[SourceClassificationRead]
    reach_metrics: list[SourceReachMetricRead]
    feeds: list[FeedRead]
