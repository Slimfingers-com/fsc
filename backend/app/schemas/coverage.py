from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.coverage.provider import (
    CoverageGapKind,
    MissingPerspectiveKind,
)


class CoverageSummaryRead(BaseModel):
    id: UUID
    story_id: UUID
    article_count: int = Field(ge=1)
    source_count: int = Field(ge=1)
    content_source_count: int = Field(ge=0)
    signal_source_count: int = Field(ge=0)
    independent_content_source_count: int = Field(ge=0)
    claim_group_count: int = Field(ge=1)
    shared_group_count: int = Field(ge=0)
    difference_count: int = Field(ge=0)
    attributed_group_count: int = Field(ge=0)
    source_type_counts: dict[str, int]
    coverage_scope_counts: dict[str, int]
    country_counts: dict[str, int]
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class CoverageGapRead(BaseModel):
    id: UUID
    story_id: UUID
    gap_kind: CoverageGapKind
    observed_count: int = Field(ge=0)
    minimum_expected: int | None = Field(default=None, ge=0)
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class MissingPerspectiveRead(BaseModel):
    id: UUID
    story_id: UUID
    claim_group_id: UUID
    representative_claim_text: str
    missing_kind: MissingPerspectiveKind
    contradiction_relation_ids: list[UUID]
    analysis_provider: str
    analysis_version: str
    analyzed_at: datetime


class CoverageGapPageRead(BaseModel):
    items: list[CoverageGapRead]
    total: int
    page: int
    page_size: int
    pages: int


class MissingPerspectivePageRead(BaseModel):
    items: list[MissingPerspectiveRead]
    total: int
    page: int
    page_size: int
    pages: int
